from django.db import models
from coredata.models import CAMPUS_CHOICES, Person, Member, CourseOffering, Semester, Unit
from jsonfield import JSONField
from courselib.json_fields import getter_setter #, getter_setter_2
import decimal

class TUG(models.Model):
    """
    Time use guideline filled out by instructors
    
    Based on form in Appendix C (p. 73) of the collective agreement:
    http://www.tssu.ca/wp-content/uploads/2010/01/CA-2004-2010.pdf
    """	
    member = models.ForeignKey(Member, null=False)
    base_units = models.DecimalField(max_digits=4, decimal_places=2, blank=False, null=False)
    last_update = models.DateField(auto_now=True)
    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff:
        # t.config['prep']: Preparation for labs/tutorials
        # t.config['meetings']: Attendance at planning meetings with instructor
        # t.config['lectures']: Attendance at lectures
        # t.config['tutorials']: Attendance at labs/tutorials
        # t.config['office_hours']: Office hours/student consultation
        # t.config['grading']
        # t.config['test_prep']: Quiz/exam preparation and invigilation
        # t.config['holiday']: Holiday compensation
        # Each of the above is a dictionary like:
        #     {
        #     'weekly': 2.0,
        #     'total': 26.0,
        #     'note': 'if more is required, we can revisit',
        #     }
        # t.config['other1']
        # t.config['other2']
        # As the other fields, but adding 'label'.
    
    regular_default = {'weekly': 0, 'total': 0, 'comment': ''}
    regular_fields = ['prep', 'meetings', 'lectures', 'tutorials', 'office_hours',
                  'grading', 'test_prep', 'holiday']
    other_default = {'label': '', 'weekly': 0, 'total': 0, 'comment': ''}
    other_fields = ['other1', 'other2']
    all_fields = regular_fields + other_fields
    
    defaults = dict([(field, regular_default) for field in regular_fields] + 
        [(field, other_default) for field in other_fields])
    
    #prep_weekly, set_prep_weekly = getter_setter_2('prep', 'weekly')

    def __unicode__(self):
        return "TA: %s  Base Units: %s" % (self.member.person.userid, self.base_units)

LEVEL_CHOICES = (
    ('NONE', 'None'),
    ('SOME', 'Some'),
    ('EXPR', 'Expert'),
)

class Skill(models.Model):
    """
    Skills an applicant specifies in their application.  Skills are specific to a department.
    """
    name = models.CharField(max_length=30)
    department = models.ForeignKey(Unit)
    level = models.CharField(max_length=4, choices=LEVEL_CHOICES)
    
    def __unicode__(self):
        return "Name: %s  Level: %s" % (self.name, self.level)


CATEGORY_CHOICES = (
        ('PHD', 'PhD'),
        ('MAS', 'Masters'),
        ('UGR', 'Undergrad'),
        ('EXT', 'External'),
        )

class TAApplication(models.Model):
    """
    TA application filled out by students
    """
    person = models.ForeignKey(Person)
    semester = models.ForeignKey(Semester)
    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    department = models.ForeignKey(Unit)
    base_units = models.DecimalField(max_digits=4, decimal_places=2)
    sin = models.PositiveIntegerField(unique=True)
    #Campus will be a csv separated field
    campus_prefered = models.CharField(max_length=30)
    skills = models.ManyToManyField(Skill) 
    experience =  models.TextField(blank=True, null=True,
        verbose_name="Experience",
        help_text='Describe any other experience that you think may be relevant to these courses.')
    course_load = models.TextField(verbose_name="Students intended course load.",
        help_text='Describe the intended course load of the semester being applied for.')
    other_support = models.TextField(blank=True, null=True,
        verbose_name="Other financial support",
        help_text='Describe any other funding you expect to receive this semester (grad students only).')
    comments = models.TextField(verbose_name="Additional comments", blank=True, null=True)
    
    class Meta:
        unique_together = (('person', 'semester', 'department'),)
    def __unicode__(self):
        return "Person: %s  Semester: %s" % (self.person, self.semester)


#what are the appointment categories?
"""APPOINTMENT_CHOICES = (
        ('GTA1', 'GTA1: ') 
        )"""

class TAContract(models.Model):
    """    
    TA Contract
    """
    person = models.ForeignKey(Person)
    department = models.ForeignKey(Unit)
    appt_start = models.DateField()
    appt_end = models.DateField()
    pay_start = models.DateField()
    pay_end = models.DateField()
    position_number = models.DecimalField(max_digits=5, decimal_places=0)
    #appt_category = models.CharField(max_length=4, choices=APPOINTMENT_CHOICES)
    init_appt = models.BooleanField(verbose_name="Initial appointment to this position")
    other_appt = models.BooleanField(verbose_name="Reappointment to same position or revision to appointment")
    sin = models.PositiveIntegerField(unique=True)
    
    ##need to clarify how to deal with courses and BU to calculate salary and scholarship
    
    remarks = models.TextField(verbose_name="Remarks")
    deadline = models.DateField()
    appt_cond = models.BooleanField()
    appt_tssu = models.BooleanField()


TAKEN_CHOICES = (
        ('YES', 'Yes: this course at SFU'),
        ('SIM', 'Yes: a similar course elsewhere'),
        ('KNO', 'No, but I know the course material'),
        ('NO', 'No, I don\'t know the material well'),
        )
EXPER_CHOICES = (
        )

class CoursePreference(models.Model):
    app = models.ForeignKey(TAApplication)
    course = models.ForeignKey(CourseOffering)
    taken = models.CharField(max_length=3, choices=TAKEN_CHOICES, blank=False, null=False)
    exper = models.CharField(max_length=3, choices=EXPER_CHOICES, blank=False, null=False)

    def __unicode__(self):
        return "Course: %s  Taken: %s" % (self.course, self.taken)
