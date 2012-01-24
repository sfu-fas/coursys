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
    #set of supervisor info   

#### change to supervisor model
    supervisor_suggested = models.TextField('Suggested Potential Supervior', max_length=250, blank=True)
    supervisor_potential = models.CharField('Potential Supervisor', max_length = 100, blank=True)
    supervisor_senior = models.CharField('Senior Supervisor', max_length = 100, blank=True)
    supervisor_second = models.CharField('Second Supervisor', max_length = 100, blank=True)
    supervisor_third = models.CharField('Third Supervisor', max_length = 100, blank=True)
    supervisor_fourth = models.CharField('Fourth Supervisor', max_length = 100, blank=True)
#### -------------------------------
    
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
    
#class Supervisor(models.Model):
#    student = ForeignKey(GradStudent)
#    supervisor = ForeignKey(Person)
#    external = models.CharField(...)

class GradStudentForm(ModelForm):
    class Meta:
        model = GradStudent
