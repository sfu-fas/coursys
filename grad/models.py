from django.db import models
from coredata.models import Person, Unit, Semester
from django.forms.models import ModelForm

GENDER_CHOICES = (
    (u'M', u'Male'),
    (u'F', u'Female'),
    (u'O', u'Other')
)

CAMPUS_CHOICES = (
        ('BRNBY', 'Burnaby Campus'),
        ('SURRY', 'Surrey Campus'),
        ('VANCR', 'Harbour Centre'),
        ('OFFST', 'Off-campus'),
        ('GNWC', 'Great Northern Way Campus'),
        ('METRO', 'METRO'),
        )

class GradStudent(models.Model):
    person = models.ForeignKey(Person, unique=True)    
    degree_program = models.CharField('Degree Program', max_length=50)
    starting_semester = models.ForeignKey(Semester, related_name='grad_starting_semester', blank=True, null=True,)
    ending_semester = models.ForeignKey(Semester, related_name='grad_ending_semester', blank=True, null=True)
    research_area = models.CharField('Research Area', max_length=200, blank=True)
    card_access_num = models.IntegerField(null=True, blank=True)
    
#### change to a db table instead
    campus = models.CharField(max_length=5, choices=CAMPUS_CHOICES, blank=True)
    
#### change to list of instructors instead
    supervisor_potential = models.CharField('Potential Supervisor', max_length = 100, blank=True)
    supervisor_senior = models.CharField('Senior Supervisor', max_length = 100, blank=True)
    supervisor_second = models.CharField('Second Supervisor', max_length = 100, blank=True)
    supervisor_thrid = models.CharField('Third Supervisor', max_length = 100, blank=True)
    supervisor_fourth = models.CharField('Fourth Supervisor', max_length = 100, blank=True)
    
#    def __unicode__(self):
#        return self.grad   
    #gender = models.CharField(max_length=2, choices=GENDER_CHOICES)
    
    

class GradStudentForm(ModelForm):
    class Meta:
        model = GradStudent
