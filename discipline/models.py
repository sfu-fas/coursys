from django.db import models
from coredata.models import Member
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from autoslug import AutoSlugField
from django.core.files.storage import FileSystemStorage
from django.conf import settings

CONTACT_CHOICES = (
        ('NONE', 'Not yet contacted'),
        ('MAIL', 'Student emailed (by system)'),
        ('OTHR', 'Instructor contacted student (outside of this system)'),
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
        ('F', 'grade of \u201CF\u201D in the course'),
        ('FD', 'grade of \u201CFD\u201D in the course'),
        ('OTHE', 'other penalty: see rationale'),
        )
DisciplineSystemStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)

class DisciplineCase(models.Model):
    student = models.ForeignKey(Member, help_text="The student this case concerns")
    notes = models.TextField(blank=True, null=True, help_text='Notes about the case (private notes)')
    def autoslug(self):
        return self.student.person.userid
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with='student__offering')
    
    # fields for instructor
    intro = models.TextField(blank=True, null=True, verbose_name="Introductory Sentence",
            help_text='You should "outline the nature of the concern", written to the student.  e.g. "On assignment 1, you submitted work very similar to another student."')
    contacted = models.CharField(max_length=4, choices=CONTACT_CHOICES, default="NONE", verbose_name="Student Contacted?",
            help_text='Has the student been informed of the case?')
    response = models.CharField(max_length=4, choices=RESPONSE_CHOICES, default="WAIT", verbose_name="Student Response",
            help_text='Has the student responded to a meeting')
    
    meeting_date = models.DateField(blank=True, null=True, help_text='Date of meeting with student (if applicable)')
    meeting_summary = models.TextField(blank=True, null=True, help_text='Summary of the meeting with student (included in letter)')
    meeting_notes = models.TextField(blank=True, null=True, help_text='Notes about the meeting with student (private notes)')
    
    facts = models.TextField(blank=True, null=True, verbose_name="Facts of the Case",
            help_text='Summary of the facts of the case (included in letter)')
    instr_penalty = models.CharField(max_length=4, choices=INSTR_PENALTY_CHOICES, default="WAIT", verbose_name="Instructor Penalty",
            help_text='Penalty assigned by the instructor for this case.')
    refer_chair = models.BooleanField(default=False, help_text='Refer case to the Chair/Director?', verbose_name="Refer to chair?")
    penalty_reason = models.TextField(blank=True, null=True, verbose_name="Penalty Rationale",
            help_text='Rationale for assigned penalty, or notes concerning penalty (included in letter)')
    
    instr_done = models.BooleanField(default=False, verbose_name="Closed?", help_text='Case closed for the instructor?')
    
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
    
    chair_done = models.BooleanField(default=False, verbose_name="Closed?", help_text='Case closed for the Chair/Director?')
    

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

