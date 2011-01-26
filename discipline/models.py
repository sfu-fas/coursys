from django.db import models
from coredata.models import Person, Member, CourseOffering
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.core.urlresolvers import reverse
from autoslug import AutoSlugField
from django.core.files.storage import FileSystemStorage
from django.utils.text import wrap
from django.conf import settings
from discipline.content import *

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
        ('ZERO', u'assign a grade of \u201CF\u201D for the work'),
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
        ('WAIT', 'Not yet contacted'),
        ('MAIL', 'Letter emailed (by system)'),
        ('OTHR', 'Letter delivered (outside of this system)'),
        )
DisciplineSystemStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)

STEP_VIEW = { # map of field -> view function ("edit_foo") that is used to edit it.
        'notes': 'notes',
        'related': 'related',
        'intro': 'intro',
        'contacted': 'contacted',
        'response': 'response',
        'meeting_date': 'meeting',
        'meeting_summary': 'meeting',
        'meeting_notes': 'meeting',
        'facts': 'facts',
        'instr_penalty': 'instr_penalty',
        'refer_chair': 'instr_penalty',
        'penalty_reason': 'instr_penalty',
        'letter_sent': 'letter_sent',
        }
STEP_TEXT = { # map of field -> description of what the step
        'notes': 'edit your notes on the case',
        'intro': 'edit the introductory sentence',
        'contacted': 'contact the student regarding the case',
        'response': "enter details of the student's response",
        'meeting_date': "enter details of the student meeting/email",
        'meeting_summary': "enter a summary of the student meeting/email",
        'facts': "summarize the facts of the case",
        'instr_penalty': 'assign a penalty',
        'letter_sent': "send instructor's letter",
        }
STEP_DESC = { # map of field/form -> description of what it is
        'notes': 'instructor notes',
        'related': 'related items',
        'intro': 'introductory sentence',
        'contacted': 'initial contact information',
        'response': 'student response details',
        'meeting': 'student meeting/email details',
        'meeting_date': 'student meeting/email details',
        'meeting_summary': 'student meeting/email details',
        'meeting_notes': 'student meeting/email details',
        'facts': 'facts of the case',
        'instr_penalty': 'penalty (from instructor)',
        'refer_chair': 'penalty (from instructor)',
        'penalty_reason': 'penalty (from instructor)',
        'letter_sent': "instructor's letter",
        }


class DisciplineGroup(models.Model):
    """
    A set of discipline cases that are related.
    """
    name = models.CharField(max_length=60, blank=False, null=False, verbose_name="Group Name",
            help_text='An arbitrary "name" for this group of cases') #.  Will be auto-generated if left blank.')
    offering = models.ForeignKey(CourseOffering, help_text="The course this group is associated with")
    slug = AutoSlugField(populate_from='name', null=False, editable=False, unique_with='offering')
    
    def __unicode__(self):
        return "%s in %s" % (self.name, self.offering)
    def get_absolute_url(self):
        return reverse('discipline.views.showgroup', kwargs={'course_slug': self.offering.slug, 'group_slug': self.slug})
    class Meta:
        unique_together = (("name", "offering"),)


class DisciplineCase(models.Model):
    """
    A case for a single student.
    """
    student = models.ForeignKey(Member, help_text="The student this case concerns.")
    instructor = models.ForeignKey(Person, help_text="The instructor who created this case.")
    notes = models.TextField(blank=True, null=True, help_text='Notes about the case (private notes, <a href="http://en.wikipedia.org/wiki/Textile_%28markup_language%29">Textile markup</a> allowed).')
    def autoslug(self):
        return self.student.person.userid
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with='student__offering')
    group = models.ForeignKey(DisciplineGroup, null=True, blank=True, help_text="Group this case belongs to (if any).")
    
    # fields for instructor
    intro = models.TextField(blank=True, null=True, verbose_name="Introductory Sentence",
            help_text=u'You should "outline the nature of the concern", written to the student&mdash;this sentence will be the introduction of the initial email to the student (plain text).  e.g. "On assignment 1, you submitted work very similar to another student."')
    contacted = models.CharField(max_length=4, choices=CONTACT_CHOICES, default="NONE", verbose_name="Student Contacted?",
            help_text='Has the student been informed of the case?')
    response = models.CharField(max_length=4, choices=RESPONSE_CHOICES, default="WAIT", verbose_name="Student Response",
            help_text='Has the student responded to the initial contact?')
    
    meeting_date = models.DateField(blank=True, null=True, verbose_name="Meeting/Email Date", help_text='Date of meeting/email with student.')
    meeting_summary = models.TextField(blank=True, null=True, verbose_name="Meeting/Email Summary", help_text='Summary of the meeting/email with student (included in letter, <a href="http://en.wikipedia.org/wiki/Textile_%28markup_language%29">Textile markup</a> allowed).')
    meeting_notes = models.TextField(blank=True, null=True, verbose_name="Meeting/Email Notes", help_text='Notes about the meeting/email with student (private notes, <a href="http://en.wikipedia.org/wiki/Textile_%28markup_language%29">Textile markup</a> allowed).')
    
    facts = models.TextField(blank=True, null=True, verbose_name="Facts of the Case",
            help_text='Summary of the facts of the case (included in letter, <a href="http://en.wikipedia.org/wiki/Textile_%28markup_language%29">Textile markup</a> allowed).  This should be a summary of the case from the instructor\'s perspective.')
    instr_penalty = models.CharField(max_length=4, choices=INSTR_PENALTY_CHOICES, default="WAIT",
            verbose_name="Instructor Penalty",
            help_text='Penalty assigned by the instructor for this case.')
    refer_chair = models.BooleanField(default=False, help_text='Refer this case to the Chair/Director?', verbose_name="Refer to chair?")
    penalty_reason = models.TextField(blank=True, null=True, verbose_name="Penalty Rationale",
            help_text='Rationale for assigned penalty, or notes/details concerning penalty.  Optional but recommended. (included in letter, <a href="http://en.wikipedia.org/wiki/Textile_%28markup_language%29">Textile markup</a> allowed)')
    
    letter_sent = models.CharField(max_length=4, choices=LETTER_CHOICES, default="WAIT", verbose_name="Letter Sent?",
            help_text='Has the letter been sent to the student and Chair/Director?')
    instr_done = models.BooleanField(default=False, verbose_name="Closed?", 
            help_text='Case closed for the instructor?')
    
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
        if self.group:
            return '%s: "%s" (in %s)' % (self.student.person.userid, self.intro, self.group.name)
        else:
            return '%s: "%s"' % (self.student.person.userid, self.intro)

    def get_absolute_url(self):
        return reverse('discipline.views.show', kwargs={'course_slug': self.student.offering.slug, 'case_slug': self.slug})

    def get_refer_chair_display(self):
        if self.refer_chair:
            return "Yes"
        else:
            return "No"
    
    def next_step(self):
        """
        Return next field that should be dealt with
        """
        if not self.intro:
            return "intro"
        elif self.contacted=="NONE":
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
        elif self.letter_sent=="WAIT":
            return "letter_sent"
        elif not self.instr_done:
            return "instr_done"
        # TODO: Chair steps

    def next_step_url(self):
        """
        The URL to edit view for the next step.
        """
        step = self.next_step()
        return reverse('discipline.views.edit_'+STEP_VIEW[step],
            kwargs={'course_slug':self.student.offering.slug, 'case_slug': self.slug})

    def next_step_text(self):
        """
        The text description of the next step.
        """
        step = self.next_step()
        return STEP_TEXT[step]
    
    def contact_email(self):
        """
        Contact email to the student (as arguments to send_mail())
        
        Use like: send_mail(*case.contact_email())
        """
        message = EMAIL_TEMPLATE.substitute(introsentence=self.intro)
        return (
            'Academic dishonsty in %s' % (self.student.offering), # subject
            wrap(message, 72), # message body
            self.instructor.email(), # from email
            [self.student.person.email(), self.instructor.email()] #recipients
            )


class RelatedObject(models.Model):
    """
    Another object within the system that is related to this case: private for instructor
    """
    case = models.ForeignKey(DisciplineCase)
    name = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')


class CaseAttachment(models.Model):
    """
    A piece of evidence to attach to a case
    """
    case = models.ForeignKey(DisciplineCase)
    name = models.CharField(max_length=255, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
        
    def upload_to(instance, filename):
        """
        path to upload case attachment
        """
        fullpath = os.path.join(
            instance.student.activity.offering.slug,
            instance.activity.slug + "_discipline",
            datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + "_" + str(instance.created_by),
            filename.encode('ascii', 'ignore'))
        return fullpath 

    attachment = models.FileField(upload_to=upload_to, max_length=500)
    mediatype = models.CharField(null=True, blank=True, max_length=200)

