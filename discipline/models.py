from django.db import models
from coredata.models import Person, Member, CourseOffering
from grades.models import Activity
from django.http import Http404
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.core.urlresolvers import reverse
from autoslug import AutoSlugField
from django.core.files.storage import FileSystemStorage
from django.utils.text import wrap
from django.conf import settings
from django.shortcuts import get_object_or_404
import string, os, datetime, json

CONTACT_CHOICES = (
        ('NONE', 'Not yet contacted'),
        ('MAIL', 'Student emailed (by system)'),
        ('OTHR', 'Instructor contacted student (outside of this system)'),
        )
RESPONSE_CHOICES = (
        ('WAIT', 'Waiting for response'),
        ('NONE', 'No response from student (after a reasonable period of time)'),
        ('DECL', 'Student declined to meet'),
        ('MAIL', 'Student sent statement by email'),
        ('MET', 'Met with student'),
        )
INSTR_PENALTY_CHOICES = (
        ('WAIT', 'penalty not yet assigned'),
        ('NONE', 'case dropped: no penalty assigned'),
        ('WARN', 'give the student a warning'),
        ('REDO', 'require the student to redo the work, or to do supplementary work'),
        ('MARK', 'assign a low grade for the work'),
        ('ZERO', u'assign a grade of \u201CF\u201D or zero for the work'),
        )
CHAIR_PENALTY_CHOICES = (
        ('WAIT', 'penalty not yet assigned'),
        ('NONE', 'no further penalty assigned'),
        ('REPR', 'formal reprimand to the student'),
        ('GRAD', 'grade penalty less severe than failure'),
        ('F', u'grade of \u201CF\u201D in the course'),
        ('FD', u'grade of \u201CFD\u201D in the course'),
        ('OTHE', 'other penalty: see rationale'),
        )
LETTER_CHOICES = (
        ('WAIT', 'Not yet sent'),
        ('MAIL', 'Letter emailed (by system)'),
        ('OTHR', 'Letter delivered (outside of this system)'),
        )
INSTR_STEPS = ['contacted', 'response', 'meeting', 'meeting_date', 'meeting_summary', 'facts', 'instr_penalty']
INSTR_FINAL = ['letter_review', 'letter_sent', 'penalty_implemented']
DisciplineSystemStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)

STEP_VIEW = { # map of field/form -> view function ("edit_foo") that is used to edit it.
        'notes': 'notes',
        'related': 'related',
        'attach': 'attach',
        'contacted': 'contacted',
        'response': 'response',
        'meeting': 'meeting',
        'meeting_date': 'meeting',
        'meeting_summary': 'meeting',
        'meeting_notes': 'meeting',
        'facts': 'facts',
        'instr_penalty': 'instr_penalty',
        'refer_chair': 'instr_penalty',
        'penalty_reason': 'instr_penalty',
        'letter_review': 'letter_review',
        'letter_sent': 'letter_sent',
        'penalty_implemented': 'penalty_implemented',
        }
STEP_TEXT = { # map of field -> description of what the step
        'notes': 'edit your notes on the case',
        'contacted': 'contact the student regarding the case',
        'response': "enter details of the student's response",
        'meeting_date': "enter details of the student meeting/email",
        'meeting_summary': "enter a summary of the student meeting/email",
        'facts': "summarize the facts of the case",
        'instr_penalty': 'assign a penalty',
        'letter_review': 'review letter to student',
        'letter_sent': "send instructor's letter",
        'penalty_implemented': "confirm penalty has been implemented",
        }
STEP_DESC = { # map of field/form -> description of what is being edited
        'notes': 'instructor notes',
        'related': 'related items',
        'attach': 'attached files',
        'contacted': 'initial contact information',
        'contact_date': 'initial contact date',
        'contact_email_text': 'initial contact email text',
        'response': 'student response details',
        'meeting': 'student meeting/email details',
        'meeting_date': 'student meeting/email date',
        'meeting_summary': 'student meeting/email summary',
        'meeting_notes': 'student meeting/email notes',
        'facts': 'facts of the case',
        'instr_penalty': 'penalty (from instructor)',
        'refer_chair': 'Chair/Director referral',
        'penalty_reason': 'penalty rationale',
        'letter_review': 'review status',
        'letter_sent': "instructor's letter status",
        'penalty_implemented': 'penalty confirmation'
        }
TEMPLATE_FIELDS = { # fields that can have a template associated with them
        'notes': 'instructor notes',
        'contact_email_text': 'initial contact email',
        'response': 'student response details',
        'meeting_summary': 'student meeting/email summary',
        'meeting_notes': 'student meeting/email notes',
        'facts': 'facts of the case',
        'penalty_reason': 'penalty rationale',
        }
TEXTILENOTE = '<a href="javascript:textile_popup()">Textile markup</a> and <a href="javascript:substitution_popup()">case substitutions</a> allowed'
TEXTILEONLYNOTE = '<a href="javascript:substitution_popup()">Case substitutions</a> allowed'

# from django/template/defaultfilters.py 
_base_js_escapes = (
    ('\\', r'\u005C'),
    ('\'', r'\u0027'),
    ('"', r'\u0022'),
    ('>', r'\u003E'),
    ('<', r'\u003C'),
    ('&', r'\u0026'),
    ('=', r'\u003D'),
    ('-', r'\u002D'),
    (';', r'\u003B'),
    (u'\u2028', r'\u2028'),
    (u'\u2029', r'\u2029')
)

# Escape every ASCII character with a value less than 32.
_js_escapes = (_base_js_escapes +
               tuple([('%c' % z, '\\u%04X' % z) for z in range(32)]))

def escapejs(value):
    """Hex encodes characters for use in JavaScript strings."""
    for bad, good in _js_escapes:
        value = value.replace(bad, good)
    return value



class DisciplineGroup(models.Model):
    """
    A set of discipline cases that are related.
    """
    name = models.CharField(max_length=60, blank=False, null=False, verbose_name="Group Name",
            help_text='An arbitrary "name" for this group of cases')
    offering = models.ForeignKey(CourseOffering, help_text="The course this group is associated with")
    slug = AutoSlugField(populate_from='name', null=False, editable=False, unique_with='offering')
    
    def __unicode__(self):
        return "%s in %s" % (self.name, self.offering)
    def get_absolute_url(self):
        return reverse('discipline.views.showgroup', kwargs={'course_slug': self.offering.slug, 'group_slug': self.slug})
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
        try:
            case = DisciplineCase.objects.get(id=self.id)
        except DisciplineCase.DoesNotExist:
            case = DisciplineCaseNonStudent.objects.get(id=self.id)
        return case
    
    instructor = models.ForeignKey(Person, help_text="The instructor who created this case.")
    offering = models.ForeignKey(CourseOffering)
    notes = models.TextField(blank=True, null=True, help_text='Notes about the case (private notes, '+TEXTILENOTE+').')
    def autoslug(self):
        return self.student.userid
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with='offering')
    group = models.ForeignKey(DisciplineGroup, null=True, blank=True, help_text="Group this case belongs to (if any).")
    
    # fields for instructor
    contact_email_text = models.TextField(blank=True, null=True, verbose_name="Contact Email Text",
            help_text=u'The initial email sent to the student regarding the case. ('+TEXTILEONLYNOTE+'.)')
    contacted = models.CharField(max_length=4, choices=CONTACT_CHOICES, default="NONE", verbose_name="Student Contacted?",
            help_text='Has the student been informed of the case?')
    contact_date = models.DateField(blank=True, null=True, verbose_name="Initial Contact Date", help_text='Date of initial contact with student regarding the case.')
    response = models.CharField(max_length=4, choices=RESPONSE_CHOICES, default="WAIT", verbose_name="Student Response",
            help_text='Has the student responded to the initial contact?')
    
    meeting_date = models.DateField(blank=True, null=True, verbose_name="Meeting/Email Date", help_text='Date of meeting/email with student.')
    meeting_summary = models.TextField(blank=True, null=True, verbose_name="Meeting/Email Summary", help_text='Summary of the meeting/email with student (included in letter, '+TEXTILENOTE+').')
    meeting_notes = models.TextField(blank=True, null=True, verbose_name="Meeting/Email Notes", help_text='Notes about the meeting/email with student (private notes, '+TEXTILENOTE+').')
    
    facts = models.TextField(blank=True, null=True, verbose_name="Facts of the Case",
            help_text='Summary of the facts of the case (included in letter, '+TEXTILENOTE+').  This should be a summary of the case from the instructor\'s perspective.')
    instr_penalty = models.CharField(max_length=4, choices=INSTR_PENALTY_CHOICES, default="WAIT",
            verbose_name="Instructor Penalty",
            help_text='Penalty assigned by the instructor for this case.')
    refer_chair = models.BooleanField(default=False, help_text='Refer this case to the Chair/Director?', verbose_name="Refer to chair?")
    penalty_reason = models.TextField(blank=True, null=True, verbose_name="Penalty Rationale",
            help_text='Rationale for assigned penalty, or notes/details concerning penalty.  Optional but recommended. (included in letter, '+TEXTILENOTE+')')
    
    letter_review = models.BooleanField(default=False, verbose_name="Reviewed?", 
            help_text='Has instructor reviewed the letter before sending?')
    letter_sent = models.CharField(max_length=4, choices=LETTER_CHOICES, default="WAIT", verbose_name="Letter Sent?",
            help_text='Has the letter been sent to the student and Chair/Director?')
    letter_text = models.TextField(blank=True, null=True, verbose_name="Letter Text")
    penalty_implemented = models.BooleanField(default=False, verbose_name="Penalty Implemented?", 
            help_text='Has instructor implemented the assigned penalty?')
    
    # fields for chair/director
    chair_meeting_date = models.DateField(blank=True, null=True,
            help_text='Date of meeting with student and Chair/Director (if applicable)')
    chair_meeting_summary = models.TextField(blank=True, null=True,
            help_text='Summary of the meeting with student and Chair/Director (appended to letter)')
    chair_meeting_notes = models.TextField(blank=True, null=True,
            help_text='Notes about the meeting with student and Chair/Director(private notes)')
    chair_penalty = models.CharField(max_length=4, choices=CHAIR_PENALTY_CHOICES, default="WAIT",
            help_text='Penalty assigned by the Chair/Director for this case.')
    chair_penalty_reason = models.TextField(blank=True, null=True, verbose_name="Penalty Rationale",
            help_text='Rationale for penalty assigned by Chair/Director, or notes concerning penalty (appended to letter)')
    refer_ubsc = models.BooleanField(default=False, help_text='Refer case to the UBSD?', verbose_name="Refer UBSD?")
    
    chair_letter_sent = models.CharField(max_length=4, choices=LETTER_CHOICES, default="WAIT", verbose_name="Chair's Letter Sent?",
            help_text='Has the letter been sent to the student and Student Services?')
    chair_done = models.BooleanField(default=False, verbose_name="Closed?", help_text='Case closed for the Chair/Director?')

    def __unicode__(self):
        return str(self.id)

    def get_absolute_url(self):
        return reverse('discipline.views.show', kwargs={'course_slug': self.student.offering.slug, 'case_slug': self.slug})

    def get_refer_chair_display(self):
        if self.refer_chair:
            return "Yes"
        else:
            return "No"
    def get_letter_review_display(self):
        if self.letter_review:
            return "Yes"
        else:
            return "No"
    def get_penalty_implemented_display(self):
        if self.penalty_implemented:
            return "Yes"
        else:
            return "No"
    def public_attachments(self):
        return CaseAttachment.objects.filter(case=self, public=True)
    def related_activities(self):
        return [ro for ro in self.relatedobject_set.all() if isinstance(ro.content_object, Activity)]
    def instr_done(self):
        return self.penalty_implemented
    
    def groupmembersJSON(self):
        """
        Return list of other group cases as a JSON object.
        """
        if not self.group:
            return json.dumps([])
        
        return json.dumps(
                [{"id": c.id,
                  "name": "%s (%s)" % (c.subclass().student.name(), c.subclass().student_userid() )}
                for c in self.group.disciplinecasebase_set.exclude(pk=self.pk)]
                )
    
    def next_step(self):
        """
        Return next field that should be dealt with
        """
        if self.contacted=="NONE":
            return "contacted"
        elif self.response=="WAIT":
            return "response"
        elif self.response in ["MET", "MAIL"] and not self.meeting_date:
            return "meeting_date"
        elif self.response in ["MET", "MAIL"] and not self.meeting_summary:
            return "meeting_summary"
        elif not self.facts:
            return "facts"
        elif self.instr_penalty=="WAIT":
            return "instr_penalty"
        elif self.instr_penalty=="NONE" and not self.instr_done:
            return "instr_done"
        elif not self.letter_review:
            return "letter_review"
        elif self.letter_sent=="WAIT":
            return "letter_sent"
        elif not self.penalty_implemented:
            return "penalty_implemented"
        elif not self.instr_done:
            return "instr_done"
        # TODO: Chair steps

    def next_step_url(self):
        """
        The URL to edit view for the next step.
        """
        step = self.next_step()
        return reverse('discipline.views.edit_case_info',
            kwargs={'field': STEP_VIEW[step], 'course_slug':self.offering.slug, 'case_slug': self.slug})

    def next_step_text(self):
        """
        The text description of the next step.
        """
        step = self.next_step()
        return STEP_TEXT[step]
    
    def create_infodict(self):
        """
        Create a dictionary of info about the case which can be used for template substitution.
        
        Dictionary is cached as self.infodict.
        """
        d = {
            'FNAME': self.student.first_name,
            'LNAME': self.student.last_name,
            'COURSE': self.offering.subject + " " + self.offering.number,
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
        SUB_FIELDS = ['LNAME', 'FNAME', 'COURSE', 'ACTIVITIES']
        if not hasattr(self, 'infodict'):
            self.create_infodict()

        template = text.replace("$", "$$")
        for field in SUB_FIELDS:
            template = template.replace("{{"+field+"}}", "${"+field+"}")

        return string.Template(template).substitute(self.infodict)

    def send_contact_email(self):
        """
        Send contact email to the student and CC instructor
        """
        body = wrap(self.substitite_values(self.contact_email_text), 78)
        
        email = EmailMessage(
            subject='Academic dishonesty in %s' % (self.offering),
            body=body,
            from_email=self.instructor.email(),
            to=[self.student.email(), self.instructor.email()],
            )
        
        email.send(fail_silently=False)

    def send_letter(self):
        """
        Send instructor's letter to the student and CC instructor
        """
        from django.template.loader import render_to_string
        html_body = "<html><body>" + render_to_string('discipline/letter_body.html', { 'case': self }) + "</body></html>"
        text_body = "Letter is included here an an HTML message, or can be viewed online at this URL:\n%s" %\
            (settings.BASE_ABS_URL + reverse('discipline.views.view_letter', kwargs={'course_slug': self.offering.slug, 'case_slug': self.slug}))
        self.letter_text = html_body
        self.save()
        email = EmailMultiAlternatives(
            subject='Academic dishonesty in %s' % (self.offering),
            body=text_body,
            from_email=self.instructor.email(),
            to=[self.student.email(), self.instructor.email()],
            )
        email.attach_alternative(html_body, "text/html")
        attach = self.public_attachments()
        for f in attach:
            f.attachment.open()
            email.attach(f.filename(), f.attachment.read(), f.mediatype)
        
        email.send(fail_silently=False)


class DisciplineCase(DisciplineCaseBase):
    student = models.ForeignKey(Person, help_text="The student this case concerns.")
    
    def student_userid(self):
        return self.student.userid

class DisciplineCaseNonStudent(DisciplineCaseBase):
    emplid = models.PositiveIntegerField(max_length=9, null=True, blank=True, verbose_name="Student Number", help_text="SFU student number, if known")
    userid = models.CharField(max_length=8, null=True, blank=True, help_text='SFU Unix userid, if known')
    email = models.EmailField(null=False, blank=False)
    last_name = models.CharField(max_length=32)
    first_name = models.CharField(max_length=32)
    
    def __init__(self, *args, **kwargs):
        super(DisciplineCaseNonStudent, self).__init__(*args, **kwargs)
        self.student = self.FakePerson()
        self.student.emplid = self.emplid
        self.student.userid = self.userid
        self.student.last_name = self.last_name
        self.student.first_name = self.first_name
        self.student.emailaddr = self.email

    def student_userid(self):
        return self.email
        
    class FakePerson(object):
        """
        An object enough like a coredata.models.Person to be used in its place
        """
        def email(self):
            return self.emailaddr
        def name(self):
            return "%s %s" % (self.first_name, self.last_name)
        def sortname(self):
            return "%s, %s" % (self.last_name, self.first_name)
        


class RelatedObject(models.Model):
    """
    Another object within the system that is related to this case: private for instructor
    """
    case = models.ForeignKey(DisciplineCaseBase)
    name = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')
    # front-end handles adding some types of content_object, but can handle
    # any object that has a .short_str() method (which is used as its label)


class CaseAttachment(models.Model):
    """
    A piece of evidence to attach to a case
    """
    def upload_to(instance, filename):
        """
        path to upload case attachment
        """
        fullpath = os.path.join(
            instance.case.offering.slug,
            "_discipline",
            str(instance.case.id),
            datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
            filename.encode('ascii', 'ignore'))
        return fullpath

    case = models.ForeignKey(DisciplineCaseBase)
    name = models.CharField(max_length=255, blank=True, null=True, verbose_name="Name", help_text="Identifying name for the attachment")
    attachment = models.FileField(upload_to=upload_to, max_length=500, verbose_name="File", storage=DisciplineSystemStorage)
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
    field = models.CharField(max_length=30, null=False, choices=TEMPLATE_FIELDS.items(),
            verbose_name="Field", help_text="The field this template applies to")
    label = models.CharField(max_length=50, null=False,
            verbose_name="Label", help_text="A short label for the menu of templates")
    text = models.TextField(blank=True, null=True,
            verbose_name="Text", help_text='"The text for the template.  Templates can contain <a href="http://en.wikipedia.org/wiki/Textile_%28markup_language%29">Textile markup</a> (except the initial contact email) and substitutions described below.')
    class Meta:
        unique_together = (("field", "label"),)
    def __unicode__(self):
        return "%s: %s" % (self.field, self.label)
    def JSON_data(self):
        """
        Convert this template to a JSON snippet.
        """
        uses_act = self.text.find("{{ACTIVITIES}}") != -1 # template uses related activities?
        return {"field": self.field, "label": self.label, "text": self.text, "activities": uses_act}


