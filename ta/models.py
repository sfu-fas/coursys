from django.db import models
from coredata.models import *
from jsonfield import JSONField
from courselib.json_fields import getter_setter
import decimal

class TUG(models.Model):
    """
    Time use guideline filled out by instructors
    
    Based on form in Appendix C (p. 73) of the collective agreement:
    http://www.tssu.ca/wp-content/uploads/2010/01/CA-2004-2010.pdf
    """	
    member = models.ForeignKey(Member, null=False)
    base_units = models.DecimalField(max_digits=4, decimal_places=2, blank=False, null=False)
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

    def __unicode__(self):
        return "TA: %s  Base Units: %s" % (self.member.person.userid, self.base_units)


class CoursePreference(models.Model):
    course = models.ForeignKey(CourseOffering)
    taken = models.BooleanField(default=False)

class TAExperience(models.Model):
    course = models.ForeignKey(CourseOffering)
    base_units = models.DecimalField(max_digits=4, decimal_places=2)
    semester = models.ForeignKey(Semester)

SUPPORT_CHOICES = (
        ('SC', 'Scholarship'),
        ('RA', 'Research Assistant'),
        ('OT', 'Other'),
        )

class Support(models.Model):
    support_type = models.CharField(max_length=2, choices=SUPPORT_CHOICES)
    details = models.TextField(blank=True, null=True)

CATEGORY_CHOICES = (
        ('PHD', 'PhD'),
        ('MAS', 'Masters'),
        ('UGR', 'Undergrad'),
        ('EXT', 'External'),
        )

CAMPUS_CHOICES = (
        ('BRNBY', 'Burnaby Campus'),
        ('SURRY', 'Surrey Campus'),
        ('VANCR', 'Harbour Centre'),
        )

class Application(models.Model):
    """
    TA application filled out by students
    """
    person = models.ForeignKey(Person)
    semester = models.ForeignKey(Semester)
    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    department = models.ForeignKey(Unit)
    sin = models.PositiveIntegerField(unique=True)
    campus_prefered = models.CharField(max_length=5, choices=CAMPUS_CHOICES)
    #course_preference = models.ManyToManyField(CoursePreference, blank=False)
    #skills = 
    ta_experience =  models.ForeignKey(TAExperience, blank=True, null=True)
    course_load = models.TextField(verbose_name="Students intended course load.",
                            help_text='Describe the intended course load of the semester being applied for.')
    other_support = models.ForeignKey(Support, blank=True, null=True)
    comments = models.TextField(verbose_name="Additional comments.")
    
    def __unicode__(self):
        return "Person: %s  Semester: %s" % (self.person, self.semester)
