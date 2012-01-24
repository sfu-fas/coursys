from django.db import models
from coredata.models import Person, Unit, Semester, CAMPUS_CHOICES
from django.forms.models import ModelForm

DEGREE_PROGRAM_CHOICES = (
    ('MScThesis', 'MSc - Thesis'),
    ('MScThesis2', 'MSc - Thesis 2')
)

class GradStudent(models.Model):
    person = models.ForeignKey(Person, unique=True, help_text="* Required. Select a person.", blank=False)    
    #degree_program = models.CharField('Degree Program', max_length=50)
    #degree_program = models.ForeignKey(DegreeProgram)
    research_area = models.CharField('Research Area', max_length=250, help_text="* Required.", blank=False)
    degree_program = models.CharField('Degree Program', max_length=50, choices = DEGREE_PROGRAM_CHOICES, help_text="* Required.")
    campus = models.CharField(max_length=5, choices=CAMPUS_CHOICES, blank=True)

    english_fluency = models.CharField(max_length=10, blank = True, help_text="I.e. Read, Write, Speak, All.")
    mother_tongue = models.CharField(max_length=25, blank = True, help_text="I.e. Scottish, Chinese, French")
    is_canadian = models.NullBooleanField()
    passport_issued_by = models.CharField(max_length=25, blank = True, help_text="I.e. US, China")
    special_arrangements = models.NullBooleanField()
    comments = models.TextField(max_length=250, blank=True, help_text="Additional information.")


### Missing:
'''
    - student status model - active.. from blah blah
    - financial
    - degree requirements
'''
    
#    def __unicode__(self):
#        return self.grad   
    
class Supervisor(models.Model):
    """
    Member (or potential member) of student's supervisory committee.
    """
    student = models.ForeignKey(GradStudent)
    supervisor = models.ForeignKey(Person, null=True)
    external = models.CharField(max_length=200, blank=True, null=True)
    position = models.SmallIntegerField(null=False)
    is_senior = models.BooleanField()
    is_potential = models.BooleanField()
    
    def __unicode__(self):
        return "%s supervising %s" % (self.supervisor or external, self.student.person)

    def save(self, *args, **kwargs):
        # make sure the data is coherent: should also be in form validation for nice UI
        is_person = bool(self.supervisor)
        is_ext = bool(self.external)
        if is_person and is_ext:
            raise ValueError, "Cannot be both an SFU user and external"
        if not is_person and not is_ext:
            raise ValueError, "Must be either an SFU user or external"
        
        if self.position==1 and not self.is_senior:
            raise ValueError, "First supervisor must be senior"
        if self.position==1 and is_ext:
            raise ValueError, "First supervisor must be internal"
        
        super(Page, self).save(*args, **kwargs)

class GradRequirement(models.Model):
    """
    A requirement that a unit has for grad students
    """
    unit = models.ForeignKey(Unit)
    description = models.CharField(max_length=100)

class CompletedRequirement(models.Model):
    """
    A requirement met by a student (or notes about them meeting it in the future)
    """
    requirement = models.ForeignKey(GradRequirement)
    student = models.ForeignKey(GradStudent)
    semester = models.ForeignKey(Semester, null=True,
            help_text="Semester when the requirement was completed")
    date = models.DateField(null=True, blank=True,
            help_text="Date the requirement was completed (optional)")
    notes = models.TextField(blank=True, help_text="Other notes")

STATUS_CHOICES = (
        ('ACTI', 'Active'),
        ('PART', 'Part-Time'),
        ('LEAV', 'On-Leave'),
        ('WIDR', 'Withdrawn'),
        ('GRAD', 'Graduated'),
        ('NOND', 'Non-degree'),
        ('GONE', 'Gone'),
        )
STATUS_ACTIVE = ('ACTI', 'PART', 'NOND') # statuses that mean "still around"
STATUS_INACTIVE = ('LEAV', 'WIDR', 'GRAD', 'GONE') # statuses that mean "not here"

class GradStatus(models.Model):
    """
    A "status" for a grad student: what were they doing in this range of semesters?
    """
    student = models.ForeignKey(GradStudent)
    status = models.CharField(max_length=4, choices=STATUS_CHOICES, blank=False)
    start = models.ForeignKey(Semester, null=False, related_name="start_semester",
            help_text="First semester of this status")
    end = models.ForeignKey(Semester, null=True, related_name="end_semester",
            help_text="Final semester of this status: blank for ongoing")
    notes = models.TextField(blank=True, help_text="Other notes")


    
class GradStudentForm(ModelForm):
    class Meta:
        model = GradStudent
