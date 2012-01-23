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
    sin = models.PositiveIntegerField(unique=True)
    campus_prefered = models.CharField(max_length=5, choices=CAMPUS_CHOICES)
    #skills = 
    experience =  models.TextField(blank=True, null=True,
        verbose_name="Experience",
        help_text='Describe any other experience that you think may be relevant to these courses.')
    course_load = models.TextField(verbose_name="Students intended course load.",
        help_text='Describe the intended course load of the semester being applied for.')
    other_support = models.TextField(blank=True, null=True,
        verbose_name="Other financial support",
        help_text='Describe any other funding you expect to receive this semester (grad students only).')
    comments = models.TextField(verbose_name="Additional comments")
    
    class Meta:
        unique_together = (('person', 'semester', 'department'),)
    def __unicode__(self):
        return "Person: %s  Semester: %s" % (self.person, self.semester)


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

