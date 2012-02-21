from django.db import models
from coredata.models import Person, Member, Course, Semester, Unit ,CourseOffering, CAMPUS_CHOICES 
from ra.models import Account
from jsonfield import JSONField
from courselib.json_fields import getter_setter #, getter_setter_2
from courselib.slugs import make_slug
from grad.views import get_semester
from autoslug import AutoSlugField
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
    
    prep = property(*getter_setter('prep'))
    meetings = property(*getter_setter('meetings'))
    lectures = property(*getter_setter('lectures'))
    tutorials = property(*getter_setter('tutorials'))
    office_hours = property(*getter_setter('office_hours'))
    grading = property(*getter_setter('grading'))
    test_prep = property(*getter_setter('test_prep'))
    holiday = property(*getter_setter('holiday'))
    other1 = property(*getter_setter('other1'))
    other2 = property(*getter_setter('other2'))
    
    @property
    def iterothers(self):
#        try:
            return (other for key, other in self.config.iteritems() 
                    if key.startswith('other')
                    and other.get('total',0) > 0)
#        except:
#            yield self.other1
#            yield self.other2 
    
    def iterfielditems(self):
        return ((field, self.config[field]) for field in self.all_fields 
                 if field in self.config)
    
    regular_default = {'weekly': 0, 'total': 0, 'comment': ''}
    regular_fields = ['prep', 'meetings', 'lectures', 'tutorials', 
            'office_hours', 'grading', 'test_prep', 'holiday']
    other_default = {'label': '', 'weekly': 0, 'total': 0, 'comment': ''}
    other_fields = ['other1', 'other2']
    all_fields = regular_fields + other_fields
    
    defaults = dict([(field, regular_default) for field in regular_fields] + 
        [(field, other_default) for field in other_fields])
    
    # depicts the above comment in code
    config_meta = {'prep':{'label':'Preparation', 
                    'help':'1. Preparation for labs/tutorials'},
            'meetings':{'label':'Attendance at planning meetings', 
                    'help':'2. Attendance at planning/coordinating meetings with instructor'}, 
            'lectures':{'label':'Attendance at lectures', 
                    'help':'3. Attendance at lectures'}, 
            'tutorials':{'label':'Attendance at labs/tutorials', 
                    'help':u'4. Attendance at labs/tutorials'}, 
            'office_hours':{'label':'Office hours', 
                    'help':u'5. Office hours/student consultation/electronic communication'}, 
            'grading':{'label':'Grading', 
                    'help':u'6. Grading\u2020',
                    'extra':u'\u2020Includes grading of all assignments, reports and examinations.'}, 
            'test_prep':{'label':'Quiz/exam preparation and invigilation', 
                    'help':u'7. Quiz preparation/assist in exam preparation/Invigilation of exams'}, 
            'holiday':{'label':'Holiday compensation', 
                    'help':u'8. Statutory Holiday Compensation\u2021',
                    'extra':u'''\u2021To compensate for all statutory holidays which  
may occur in a semester, the total workload required will be reduced by one (1) 
hour for each base unit assigned excluding the additional 0.17 B.U. for 
preparation, e.g. 4 hours reduction for 4.17 B.U. appointment.'''}}
    
    #prep_weekly, set_prep_weekly = getter_setter_2('prep', 'weekly')

    def __unicode__(self):
        return "TA: %s  Base Units: %s" % (self.member.person.userid, self.base_units)

CATEGORY_CHOICES = ( # order must match list in TAPosting.config['salary']
        ('GTA1', 'Masters'),
        ('GTA2', 'PhD'),
        ('UTA', 'Undergrad'),
        ('ETA', 'External'),
)

class TAPosting(models.Model):
    """
    Posting for one unit in one semester
    """
    semester = models.ForeignKey(Semester)
    unit = models.ForeignKey(Unit)
    opens = models.DateField(help_text='Opening date for the posting')
    closes = models.DateField(help_text='Closing date for the posting')
    def autoslug(self):
        return make_slug(self.semester.slugform() + "-" + self.unit.label)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)
    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff:
        # 'salary': default pay rates per BU for each GTA1, GTA2, UTA, EXT: ['1.00', '2.00', '3.00', '4.00']
        # 'scholarship': default scholarship rates per BU for each GTA1, GTA2, UTA, EXT
        # 'start': default start date for contracts ('YYYY-MM-DD')
        # 'end': default end date for contracts ('YYYY-MM-DD')
        # 'excluded': courses to exclude from posting (list of Course.id values)
        # 'payperiods': number of pay periods in the semeseter

    defaults = {
            'salary': ['0.00']*len(CATEGORY_CHOICES),
            'scholarship': ['0.00']*len(CATEGORY_CHOICES),
            'start': '',
            'end': '',
            'excluded': [],
            'bu_defaults': {},
            'payperiods': 14,
            }
    salary, set_salary = getter_setter('salary')
    scholarship, set_scholarship = getter_setter('scholarship')
    start, set_start = getter_setter('start')
    end, set_end = getter_setter('end')
    excluded, set_excluded = getter_setter('excluded')
    bu_defaults, set_bu_defaults = getter_setter('bu_defaults')
    payperiods, set_payperiods = getter_setter('payperiods')
    
    class Meta:
        unique_together = (('unit', 'semester'),)
    def __unicode__(self): 
        return "%s, %s" % (self.unit.name, self.semester)
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."
    
    def selectable_courses(self):
        """
        Course objects that can be selected as possible choices
        """
        excl = set(self.excluded())
        offerings = CourseOffering.objects.filter(semester=self.semester, owner=self.unit).select_related('course')
        # remove duplicates and sort nicely
        courses = list(set((o.course for o in offerings if o.course_id not in excl)))
        courses.sort()
        return courses
    
    def selectable_offerings(self):
        """
        CourseOffering objects that can be selected as possible choices
        """
        excl = set(self.excluded())
        offerings = CourseOffering.objects.filter(semester=self.semester, owner=self.unit).exclude(course__id__in=excl)
        return offerings
    
    def cat_index(self, val):
        indexer = dict((v[0],k) for k,v in enumerate(CATEGORY_CHOICES))
        return indexer.get(val)
    
    def default_bu(self, offering):
        """
        Default BUs to assign for this course offering
        """
        level = offering.number[0] + "00"
        if level not in self.bu_defaults():
            return decimal.Decimal(0)
        
        defaults = self.bu_defaults()[level]
        defaults.sort()
        count = offering.enrl_tot
        # get highest cutoff <= actual student count
        last = decimal.Decimal(0)
        for s,b in defaults:
            if s > count:
                return decimal.Decimal(last)
            last = b
        return decimal.Decimal(last) # if off the top of scale, return max

    def required_bu(self, offering):
        """
        Actual BUs to assign to this course: default + extra
        """
        default = self.default_bu(offering)
        extra = offering.extra_bu()
        return default + extra

LEVEL_CHOICES = (
    ('0_EXPR', 'Expert'),
    ('1_SOME', 'Some'),
    ('2_NONE', 'None'),
)

class Skill(models.Model):
    """
    Skills an applicant specifies in their application.  Skills are specific to a department.
    """
    name = models.CharField(max_length=30)
    unit = models.ForeignKey(Unit)
    level = models.CharField(max_length=6, choices=LEVEL_CHOICES)
    
    def __unicode__(self):
        return "Name: %s  Level: %s" % (self.name, self.get_level_display())

PREFERENCE_CHOICES = (
        ('0_PRF', 'Prefered'),
        ('1_WIL', 'Willing'),
        ('2_NOT', 'Not willing'),
)

class CampusPreference(models.Model):
    """
    Preference ranking for all campuses
    """
    campus = models.CharField(max_length=4, choices=CAMPUS_CHOICES)
    rank = models.CharField(max_length=5, choices=PREFERENCE_CHOICES)

class TAApplication(models.Model):
    """
    TA application filled out by students
    """
    posting = models.ForeignKey(TAPosting)
    person = models.ForeignKey(Person)
    category = models.CharField(max_length=4, blank=False, null=False, choices=CATEGORY_CHOICES)
    base_units = models.DecimalField(max_digits=4, decimal_places=2,
            help_text='Maximum number of base units you\'re interested in taking (5 is a "full" TA-ship)')
    sin = models.PositiveIntegerField(verbose_name="SIN",
            help_text="Your social insurance number")
    campus_preferences = models.ManyToManyField(CampusPreference)
    skills = models.ManyToManyField(Skill) 
    experience =  models.TextField(blank=True, null=True,
        verbose_name="Experience",
        help_text='Describe any other experience that you think may be relevant to these courses.')
    course_load = models.TextField(verbose_name="Intended course load",
        help_text='Describe the intended course load of the semester being applied for.')
    other_support = models.TextField(blank=True, null=True,
        verbose_name="Other financial support",
        help_text='Describe any other funding you expect to receive this semester (grad students only).')
    comments = models.TextField(verbose_name="Additional comments", blank=True, null=True)
    
    class Meta:
        unique_together = (('person', 'posting'),)
    def __unicode__(self):
        return "Person: %s  Semester: %s" % (self.person, self.semester)



DESC_CHOICES = (
        ('OML','office/marking/lab'),
        ('OM','office/marking')
    )

APPOINTMENT_CHOICES = (
        ("INIT","Initial: Initial appointment to this position"),
        ("REAP","Reappointment: Reappointment to same position or revision to appointment"),       
    )

class TAContract(models.Model):
    """    
    TA Contract, filled in by TAAD
    """
    #ta_application = models.ForeignKey(TAApplication)
    ta_posting = models.ForeignKey(TAPosting)
    applicant = models.ForeignKey(Person)
    sin = models.PositiveIntegerField(unique=True,verbose_name="SIN",help_text="Applicant's social insurance number")
    pay_start = models.DateField()
    pay_end = models.DateField()
    position_number = models.ForeignKey(Account)
    appt_category = models.CharField(max_length=4, choices=CATEGORY_CHOICES, verbose_name="Appointment Category")
    appt = models.CharField(max_length=4, choices=APPOINTMENT_CHOICES, verbose_name="Appointment")
    pay_per_bu = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Pay per Base Unit Semester Rate.",)
    scholarship_per_bu = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Scholarship per Base Unit Semester Rate.",)
    deadline = models.DateField(help_text='Deadline for acceptance')
    remarks = models.TextField(blank=True)
    appt_cond = models.BooleanField(default=False)
    appt_tssu = models.BooleanField(default=True)
    created_by = models.CharField(max_length=8, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
        
    def __unicode__(self):
        return (self.applicant)

class TACourse(models.Model):
    course = models.ForeignKey(CourseOffering, blank=False, null=False)
    contract = models.ForeignKey(TAContract)
    description = models.CharField(max_length=3, choices=DESC_CHOICES, blank=False, null=False)
    bu = models.DecimalField(max_digits=4, decimal_places=2)
    
    class Meta:
        unique_together = (('course', 'contract'),)
    def __unicode__(self):
        return "Course: %s  TA: %s" % (self.course, self.contract)
    
TAKEN_CHOICES = (
        ('YES', 'Yes: this course at SFU'),
        ('SIM', 'Yes: a similar course elsewhere'),
        ('KNO', 'No, but I know the course material'),
        ('NO', 'No, I don\'t know the material well'),
        )
EXPER_CHOICES = (
        ('TST', 'Placeholder option'),
        )

class CoursePreference(models.Model):
    app = models.ForeignKey(TAApplication)
    course = models.ForeignKey(Course)
    taken = models.CharField(max_length=3, choices=TAKEN_CHOICES, blank=False, null=False)
    exper = models.CharField(max_length=3, choices=EXPER_CHOICES, blank=False, null=False)

    def __unicode__(self):
        return "Course: %s  Taken: %s" % (self.course, self.taken)
