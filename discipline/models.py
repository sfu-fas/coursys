from courselib.json_fields import JSONField, config_property
from django.db import models
from coredata.models import Person, Member, CourseOffering, Role
from grades.models import Activity
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.urls import reverse
from django.template.loader import render_to_string
from autoslug import AutoSlugField
from django.utils.text import wrap
from django.conf import settings
from courselib.slugs import make_slug
from courselib.storage import UploadedFileStorage, upload_path
import string, os, datetime, json

CONTACT_CHOICES = (
        ('NONE', 'Not yet contacted'),
        ('MAIL', 'Student emailed through this system'),
        ('OTHR', 'Student contacted (outside of this system)'),
        )
RESPONSE_CHOICES = (
        ('WAIT', 'Waiting for response'),
        ('NONE', 'No response from student'),
        ('DECL', 'Student declined to meet'),
        ('MAIL', 'Student sent statement by email'),
        ('MET', 'Met with student'),
        )
INSTR_PENALTY_CHOICES = (
        ('WAIT', 'penalty not yet assigned'),
        ('NONE', 'case dropped: no penalty assigned'),
        ('WARN', 'give the student a written warning'),
        ('REDO', 'require the student to redo the work, or to do supplementary work'),
        ('MARK', 'assign a low grade for the work'),
        ('ZERO', 'assign a grade of \u201CF\u201D or zero for the work'),
        )
"""
CHAIR_PENALTY_CHOICES = (
        ('WAIT', 'penalty not yet assigned'),
        ('NONE', 'no further penalty assigned'),
        ('REPR', 'formal reprimand to the student'),
        ('GRAD', 'grade penalty less severe than failure'),
        ('F', 'grade of \u201CF\u201D in the course'),
        ('FD', 'grade of \u201CFD\u201D in the course'),
        ('OTHE', 'other penalty: see rationale'),
        )
"""
LETTER_CHOICES = (
        ('WAIT', 'Not yet sent'),
        ('MAIL', 'Letter emailed through this system'),
        ('OTHR', 'Instructor will deliver letter (outside of this system)'),
        )
SS_STATE_CHOICES = (
        ('WAIT', 'Waiting for instructor/chair'),
        ('UBSD', 'Case sent to UBSD'),
        ('SCOD', 'Case sent to SCODA'),
        ('DONE', 'Case completed'),
        )
INSTR_PENALTY_DICT = dict(INSTR_PENALTY_CHOICES)
INSTR_PENALTY_VALUES = set(INSTR_PENALTY_DICT.keys())


STEP_SHORT = { # map of field -> sort order and short description of the step
        'contacted': (1, 'inform student'),
        'response': (2, 'discuss with student'),
        'facts': (5, 'describe case'),
        'penalty': (6, 'penalty'),
        'letter_sent': (8, 'submit report'),
        'penalty_implemented': (9, 'record penalty'),
        }

TEMPLATE_FIELDS = { # fields that can have a template associated with them
        'notes': 'private notes',
        'notes_public': 'public notes',
        'contact_email_text': 'initial contact email',
        'response': 'student response details',
        'meeting_summary': 'student meeting/email summary',
        'meeting_notes': 'student meeting/email notes',
        'facts': 'facts of the case',
        'penalty_reason': 'penalty rationale',
        }

MAX_ATTACHMENTS = 5*1024*1024 # maximum total size for email attachments
MAX_ATTACHMENTS_TEXT = '5 MB'


class DisciplineGroup(models.Model):
    """
    A set of discipline cases that are related.
    """
    name = models.CharField(max_length=60, blank=False, null=False, verbose_name="Cluster Name",
            help_text='An arbitrary "name" for this cluster of cases')
    offering = models.ForeignKey(CourseOffering, help_text="The course this cluster is associated with", on_delete=models.PROTECT)
    def autoslug(self):
        return make_slug(self.name)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique_with='offering')
    
    def __str__(self):
        return "%s in %s" % (self.name, self.offering)
    def get_absolute_url(self):
        return reverse('offering:discipline:showgroup', kwargs={'course_slug': self.offering.slug, 'group_slug': self.slug})
    class Meta:
        unique_together = (("name", "offering"),)


class DisciplineCaseBase(models.Model):
    """
    A case for a single person: either a student in the course, or arbitrary person (depending on the subclass used).
    """
    def subclass(self):
        """
        Return the specific subclass version of this object.
        """
        for CaseClass in [DisciplineCaseInstrStudent, DisciplineCaseInstrNonStudent, DisciplineCaseChairStudent, DisciplineCaseChairNonStudent]:
            try:
                return CaseClass.objects.select_related('offering').get(id=self.id)
            except CaseClass.DoesNotExist:
                pass

        return self
    
    owner = models.ForeignKey(Person, help_text="The person who created/owns this case.", on_delete=models.PROTECT)
    offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT)
    notes = models.TextField(blank=True, null=True, verbose_name="Private Notes", help_text='Notes about the case (private notes).')
    notes_public = models.TextField(blank=True, null=True, verbose_name="Public Notes", help_text='Notes about the case (public notes).')
    def autoslug(self):
        return self.student.userid
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique_with='offering')
    group = models.ForeignKey(DisciplineGroup, null=True, blank=True, help_text="Cluster this case belongs to (if any).", on_delete=models.PROTECT)

    contact_email_text = models.TextField(blank=True, null=True, verbose_name="Contact Email Text",
            help_text='The initial email sent to the student regarding the case. Please also note the date of the email.')
    contacted = models.CharField(max_length=4, choices=CONTACT_CHOICES, default="NONE", verbose_name="Student Contacted?",
            help_text='Has the student been informed of the case?')
    contact_date = models.DateField(blank=True, null=True, verbose_name="Initial Contact Date", help_text='Date of initial contact with student regarding the case.')
    response = models.CharField(max_length=4, choices=RESPONSE_CHOICES, default="WAIT", verbose_name="Student Response",
            help_text='Has the student responded to the initial contact?')
    
    meeting_date = models.DateField(blank=True, null=True, verbose_name="Meeting/Email Date", help_text='Date of meeting/email with student.')
    meeting_summary = models.TextField(blank=True, null=True, verbose_name="Meeting/Email Summary", help_text='Summary of the meeting/email with student (included in letter).')
    meeting_notes = models.TextField(blank=True, null=True, verbose_name="Meeting/Email Notes", help_text='Notes about the meeting/email with student (private notes).')
    
    facts = models.TextField(blank=True, null=True, verbose_name="Facts of the Case",
            help_text='Summary of the facts of the case (included in letter).  This should be a summary of the case from the instructor\'s perspective.')
    penalty = models.CharField(max_length=20, default="WAIT",  # formerly choices=INSTR_PENALTY_CHOICES but now a comma-separated list of those values
            verbose_name="Instructor Penalty",
            help_text='Penalty assigned by the instructor for this case.')
    refer = models.BooleanField(default=False, help_text='Refer this case to the Chair/Director?', verbose_name="Refer to chair?")
    penalty_reason = models.TextField(blank=True, null=True, verbose_name="Penalty Rationale/Details",
            help_text='Rationale for assigned penalty, or notes/details concerning penalty.  Optional but recommended. (included in letter)')
    
    letter_review = models.BooleanField(default=False, verbose_name="Reviewed?", 
            help_text='Has instructor reviewed the letter before sending?')
    letter_sent = models.CharField(max_length=4, choices=LETTER_CHOICES, default="WAIT", verbose_name="Letter Sent?",
            help_text='Has the letter been sent to the student and Chair/Director?')
    letter_date = models.DateField(blank=True, null=True, verbose_name="Letter Date", help_text="Date instructor's letter was sent to student.")
    letter_text = models.TextField(blank=True, null=True, verbose_name="Letter Text")
    penalty_implemented = models.BooleanField(default=False, verbose_name="Penalty Implemented?", 
            help_text='Has instructor implemented the assigned penalty?')
    central_note = models.TextField(blank=True, null=True, verbose_name="Student Services Note",
                                    help_text='Additional notes about the case status (visible to student and instructor)')
    central_note_date = models.DateField(blank=True, null=True, verbose_name="Student Services Note Date",
                                    help_text='Last update to the Student Services note.')

    config = JSONField(null=False, blank=False, default=dict)

    ro_display = False # set in some views to prevent unnecessary links
    origsection = None # cache for get_origsection
    
    """
    # fields for chair/director
    chair_notes = models.TextField(blank=True, null=True, help_text='Notes about the case (private notes.')
    chair_meeting_date = models.DateField(blank=True, null=True,
            help_text='Date of meeting with student and Chair/Director (if applicable)')
    chair_meeting_summary = models.TextField(blank=True, null=True,
            help_text='Summary of the meeting with student and Chair/Director (included in letter)')
    chair_meeting_notes = models.TextField(blank=True, null=True,
            help_text='Notes about the meeting with student and Chair/Director (private notes)')
    chair_facts = models.TextField(blank=True, null=True, verbose_name="Facts of the Case from Chair/Director",
            help_text='Summary of the facts of the case (included in letter).  This should contain any additions/updates to the facts presented by the instructor.')

    chair_penalty = models.CharField(max_length=4, choices=CHAIR_PENALTY_CHOICES, default="WAIT",
            help_text='Penalty assigned by the Chair/Director for this case.')
    refer_ubsd = models.BooleanField(default=False, help_text='Refer case to the UBSD?', verbose_name="Refer UBSD?")
    chair_penalty_reason = models.TextField(blank=True, null=True, verbose_name="Penalty Rationale",
            help_text='Rationale for penalty assigned by Chair/Director, or notes concerning penalty (included in letter)')
    
    chair_letter_review = models.BooleanField(default=False, verbose_name="Chair Letter Reviewed?", 
            help_text='Has the chair/directory reviewed the letter before sending?')
    chair_letter_sent = models.CharField(max_length=4, choices=LETTER_CHOICES, default="WAIT", verbose_name="Chair's Letter Sent?",
            help_text='Has the letter been sent to the student and Student Services?')
    chair_letter_date = models.DateField(blank=True, null=True, verbose_name="Letter Date", help_text="Date chair's/director's letter was sent to student.")
    chair_letter_text = models.TextField(blank=True, null=True, verbose_name="Letter Text")
    chair_penalty_implemented = models.BooleanField(default=False, verbose_name="Penalty Implemented?", 
            help_text="Has chair's/director's been implemented?")

    # fields for student services
    ss_state = models.CharField(max_length=4, choices=SS_STATE_CHOICES, default="WAIT",
            help_text='State of the case for Student Services.')
    ss_notes = models.TextField(blank=True, null=True,
            help_text="Student Services' notes about the case (private notes)")
    """

    def __str__(self):
        return str(self.id)

    def get_absolute_url(self):
        return reverse('offering:discipline:show', kwargs={'course_slug': self.offering.slug, 'case_slug': self.slug})

    def get_origsection(self):
        if not self.origsection:
            # no cached section: look up
            self.origsection = self.membership().get_origsection()
        
        return self.origsection

    def get_refer_display(self):
        return "Yes" if self.refer else "No"

    def get_letter_review_display(self):
        return "Yes" if self.letter_review else "No"

    def get_penalty_implemented_display(self):
        return "Yes" if self.penalty_implemented else "No"

    def get_penalty_display(self):
        return '; '.join(INSTR_PENALTY_DICT[k] for k in self.penalty.split(','))

    def sendable(self):
        return self.contacted != 'NONE' and self.response != 'WAIT' and self.facts_wordcount() > 0 and self.penalty != 'WAIT'

    def done(self):
        return self.penalty=="NONE" or self.penalty_implemented

    def editable(self):
        return self.penalty != "NONE" and self.letter_sent == 'WAIT'

    def can_edit(self, field):
        """
        Can this field be modified for this case?
        
        Logic: after letter sent, can only modify penalty implemented status.
        """
        return self.letter_sent == "WAIT" or field == 'penalty_implemented'

    def caseid(self):
        if self.contact_date:
            year = "%4i" % (self.contact_date.year,)
        else:
            year = "xxxx"
        return "CMS-%s-%06i" % (year, self.pk)

    def public_attachments(self):
        return CaseAttachment.objects.filter(case=self, public=True)

    def public_attachments_size(self):
        return sum(a.attachment.size for a in self.public_attachments())

    def related_activities(self):
        return [ro for ro in self.relatedobject_set.all() if isinstance(ro.content_object, Activity)]

    def groupmembers(self):
        """
        Return list of other group cases as a JSON-able object.
        """
        if not self.group:
            return []
        else:
            return [
                {"id": c.id, "name": "%s (%s)" % (c.subclass().student.name_with_pref(), c.subclass().student_userid())}
                for c in self.group.disciplinecasebase_set.exclude(pk=self.pk)
            ]

    def groupmembersJSON(self):
        """
        Return list of other group cases as a JSON object.
        """
        if not self.group:
            return json.dumps([])

        return json.dumps(
            [{"id": c.id,
              "name": "%s (%s)" % (c.subclass().student.name_with_pref(), c.subclass().student_userid())}
             for c in self.group.disciplinecasebase_set.exclude(pk=self.pk)]
        )

    def facts_wordcount(self) -> int:
        return 0 if not self.facts else len(self.facts.split())

    def attachment_count(self) -> int:
        return CaseAttachment.objects.filter(case=self).count()

    def create_infodict(self):
        """
        Create a dictionary of info about the case which can be used for template substitution.
        
        Dictionary is cached as self.infodict.
        """
        d = {
            'FNAME': self.student.first_name,
            'LNAME': self.student.last_name,
            'COURSE': self.offering.subject + " " + self.offering.number,
            'SEMESTER': self.offering.semester.label(),
            }
        
        # get list of activities as English
        activities = self.related_activities()
        if activities:
            activities = ", ".join((ro.content_object.name for ro in activities))
            # replace the last ", " with " and "
            pos = activities.rfind(", ")
            if pos!=-1:
                activities = activities[:pos] + " and " + activities[(pos+2):]
            d['ACTIVITIES'] = activities
        else:
            # some fallback marker
            d['ACTIVITIES'] = 'ASSIGNMENT/EXAM'
        
        self.infodict = d
    
    def substitite_values(self, text):
        """
        Return field with substitutions as promised.
        """
        if text is None:
            return ''

        SUB_FIELDS = ['LNAME', 'FNAME', 'COURSE', 'ACTIVITIES', 'SEMESTER']
        if not hasattr(self, 'infodict'):
            self.create_infodict()

        template = text.replace("$", "$$")
        for field in SUB_FIELDS:
            template = template.replace("{{"+field+"}}", "${"+field+"}")

        return string.Template(template).substitute(self.infodict)

    def unfinalize(self):
        """
        Un-close the case, so the instructor can edit again.
        """
        self.letter_sent = 'WAIT'
        self.penalty_implemented = False
        self.save()


class DisciplineCaseInstr(DisciplineCaseBase):
    """
    An instructor's case
    """
    typelabel = "instructor"

    def next_step(self):
        """
        Return next field that should be dealt with
        """
        if self.contacted=="NONE":
            return "contacted"
        elif self.response=="WAIT":
            return "response"
        elif not self.facts:
            return "facts"
        elif self.penalty=="WAIT":
            return "penalty"
        elif self.penalty!="NONE" and self.letter_sent=="WAIT":
            return "letter_sent"
        elif self.penalty!="NONE" and not self.penalty_implemented:
            return "penalty_implemented"

    def next_step_short(self):
        "The short description of the next step, used by index view."
        short = STEP_SHORT[self.next_step()]
        return (10-short[0], short[1])

    def send_contact_email(self):
        """
        Send contact email to the student and CC instructor
        """
        body = self.substitite_values(self.contact_email_text)

        email = EmailMessage(
            subject='Academic dishonesty in %s' % (self.get_origsection()),
            body=body,
            from_email=self.owner.email(),
            to=[self.student.email()],
            cc=[self.owner.email()],
            )
        
        email.send(fail_silently=False)

    def letter_recipients(self):
        """
        Return collection of people who will receive the letter by email:

        student, instructor, [department CC], [university CC]
        """
        student = self.student.full_email()
        instr = self.owner.full_email()
        roles = Role.objects_fresh.filter(role="DICC", unit=self.offering.owner)
        dept = [r.person.full_email() for r in roles]
        roles = Role.objects_fresh.filter(role="DICC", unit__label="UNIV")
        univ = [r.person.full_email() for r in roles]

        return student, instr, dept, univ

    def send_letter(self, currentuser, from_central=False):
        """
        Send instructor's letter to the student and CC instructor

        from_central: this is an update email produced by Student Services
        """
        html_body = render_to_string('discipline/letter_body.html',
                                     { 'case': self, 'currentuser': currentuser, 'from_central': from_central })
        text_body = "Letter is included here as an HTML message, or can be viewed online at this URL:\n%s" %\
            (settings.BASE_ABS_URL + reverse('offering:discipline:view_letter', kwargs={'course_slug': self.offering.slug, 'case_slug': self.slug}))
        self.letter_text = html_body
        self.letter_date = datetime.date.today()
        self.letter_review = True
        self.letter_sent = 'MAIL'
        self.save()

        student, instr, dept, univ = self.letter_recipients()
        
        # instructor/student email
        email = EmailMultiAlternatives(
            subject='Academic dishonesty in %s' % (self.get_origsection()),
            body=text_body,
            from_email=currentuser.full_email() if from_central else instr,
            to=[student],
            cc=[instr, currentuser.full_email()] if from_central else [instr],
            )
        email.attach_alternative("<html><body>" + html_body + "</body></html>", "text/html")
        attach = self.public_attachments()
        for f in attach:
            f.attachment.open()
            email.attach(f.filename(), f.attachment.read(), f.mediatype)
        email.send(fail_silently=False)

        # copy for filing
        email = EmailMultiAlternatives(
            subject='Academic dishonesty in %s' % (self.get_origsection()),
            body=text_body,
            from_email=currentuser.full_email() if from_central else instr,
            to=dept + univ,
            cc=[instr],
            )
        email.attach_alternative("<html><body>" + html_body + "</body></html>", "text/html")
        attach = self.public_attachments()
        for f in attach:
            f.attachment.open()
            email.attach(f.filename(), f.attachment.read(), f.mediatype)
        
        email.send(fail_silently=False)


class DisciplineCaseInstrStudent(DisciplineCaseInstr):
    student = models.ForeignKey(Person, help_text="The student this case concerns.", on_delete=models.PROTECT)
    def is_in_course(self):
        return True
    
    def student_userid(self):
        return self.student.userid
    def membership(self):
        try:
            return Member.objects.get(offering=self.offering, person=self.student)
        except Member.MultipleObjectsReturned:
            return Member.objects.exclude(role='DROP').get(offering=self.offering, person=self.student)

    def full_name(self):
        return f'{self.student.name_with_pref()}'


class _FakePerson(object):
    """
    An object enough like a coredata.models.Person to be used in its place
    """
    def populate_from(self, obj):
        """
        Use data from the case object to populate fields needed here.
        """
        self.emplid = obj.emplid
        self.userid = obj.userid
        self.last_name = obj.last_name
        self.first_name = obj.first_name
        self.emailaddr = obj.email
            
    def email(self):
        return self.emailaddr
    def full_email(self):
        return "%s <%s>" % (self.name(), self.emailaddr)
    def name(self):
        return "%s %s" % (self.first_name, self.last_name)
    def sortname(self):
        return "%s, %s" % (self.last_name, self.first_name)


class _FakeMember(object):
    """
    An object enough like a coredata.models.Member to be used in its place
    """
    def populate_from(self, obj):
        """
        Use data from the case object to populate fields needed here.
        """
        if not hasattr(obj, 'offering'):
            return
        
        self.offering = obj.offering

    def get_origsection(self):
        return self.offering


class DisciplineCaseInstrNonStudent(DisciplineCaseInstr):
    emplid = models.PositiveIntegerField(null=True, blank=True, verbose_name="Student Number", help_text="SFU student number, if known")
    userid = models.CharField(max_length=8, null=True, blank=True, help_text='SFU Unix userid, if known')
    email = models.EmailField(null=False, blank=False)
    last_name = models.CharField(max_length=32)
    first_name = models.CharField(max_length=32)

    def is_in_course(self):
        return False
    def student_userid(self):
        return self.email
    def membership(self):
        return self.member
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    def __init__(self, *args, **kwargs):
        super(DisciplineCaseInstrNonStudent, self).__init__(*args, **kwargs)
        self.student = _FakePerson()
        self.student.populate_from(self)
        self.member = _FakeMember()
        self.member.populate_from(self)


class DisciplineCaseChair(DisciplineCaseBase):
    """
    An chair's case
    """
    instr_case = models.ForeignKey(DisciplineCaseInstr, help_text="The instructor's case that triggered this case", on_delete=models.PROTECT)


class DisciplineCaseChairStudent(DisciplineCaseChair):
    student = models.ForeignKey(Person, help_text="The student this case concerns.", on_delete=models.PROTECT)
    def is_in_course(self):
        return True
    def student_userid(self):
        return self.student.userid


class DisciplineCaseChairNonStudent(DisciplineCaseChair):
    emplid = models.PositiveIntegerField(null=True, blank=True, verbose_name="Student Number", help_text="SFU student number, if known")
    userid = models.CharField(max_length=8, null=True, blank=True, help_text='SFU Unix userid, if known')
    email = models.EmailField(null=False, blank=False)
    last_name = models.CharField(max_length=32)
    first_name = models.CharField(max_length=32)

    def is_in_course(self):
        return False
    def student_userid(self):
        return self.email
    def __init__(self, *args, **kwargs):
        super(DisciplineCaseChairNonStudent, self).__init__(*args, **kwargs)
        self.student = _FakePerson()
        self.student.populate_from(self)


class RelatedObject(models.Model):
    """
    Another object within the system that is related to this case: private for instructor
    """
    case = models.ForeignKey(DisciplineCaseBase, on_delete=models.PROTECT)
    name = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    # front-end handles adding some types of content_object, but can handle
    # any object that has a .short_str() method (which is used as its label)


def _disc_upload_to(instance, filename):
    """
    path to upload case attachment
    """
    return upload_path(instance.case.offering.slug, '_discipline', filename)


class CaseAttachment(models.Model):
    """
    A piece of evidence to attach to a case
    """
    case = models.ForeignKey(DisciplineCaseBase, on_delete=models.PROTECT)
    name = models.CharField(max_length=150, blank=True, null=True, verbose_name="Name", help_text="Identifying name for the attachment")
    attachment = models.FileField(upload_to=_disc_upload_to, max_length=500, verbose_name="File", storage=UploadedFileStorage)
    mediatype = models.CharField(null=True, blank=True, max_length=200)
    public = models.BooleanField(default=True, verbose_name="Public?", 
            help_text='Public files will be included in correspondence with student. Private files will be retained as information about the case.')

    notes = models.TextField(blank=True, null=True, verbose_name="Notes", help_text="Notes about this file (private).")

    class Meta:
        unique_together = (("case", "name"),)

    def filename(self):
        return os.path.basename(self.attachment.name)


class DisciplineTemplate(models.Model):
    """
    A text template to help fill in a field in this app.
    """
    field = models.CharField(max_length=30, null=False, choices=list(TEMPLATE_FIELDS.items()),
            verbose_name="Field", help_text="The field this template applies to")
    label = models.CharField(max_length=50, null=False,
            verbose_name="Label", help_text="A short label for the menu of templates")
    text = models.TextField(blank=False, null=False,
            verbose_name="Text", help_text='The text for the template.  Templates can contain substitutions described below.')

    class Meta:
        unique_together = (("field", "label"),)
        ordering = ('field', 'label')

    def __str__(self):
        return "%s: %s" % (self.field, self.label)

    def JSON_data(self):
        """
        Convert this template to a JSON snippet.
        """
        uses_act = self.text.find("{{ACTIVITIES}}") != -1 # template uses related activities?
        return {"field": self.field, "label": self.label, "text": self.text, "activities": uses_act}


