from django.db import models
from django.db.models import Sum
from coredata.models import Person, Member, Course, Semester, Unit ,CourseOffering, CAMPUS_CHOICES
from ra.models import Account
from jsonfield import JSONField
from courselib.json_fields import getter_setter #, getter_setter_2
from courselib.slugs import make_slug
from autoslug import AutoSlugField
import decimal, datetime
from numbers import Number
from dashboard.models import NewsItem
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django.utils.safestring import mark_safe
from creoleparser import text2html

import bu_rules

LAB_BONUS_DECIMAL = decimal.Decimal('0.17')
LAB_BONUS = float(LAB_BONUS_DECIMAL)
HOURS_PER_BU = 42 # also in media/js/ta.js

HOLIDAY_HOURS_PER_BU = decimal.Decimal('1.1')

def _round_hours(val):
    "Round to two decimal places because... come on."
    if isinstance(val, decimal.Decimal):
        return val.quantize(decimal.Decimal('.01'))
    elif isinstance(val, Number):
        return round(val, 2)
    else:
        return val

class TUG(models.Model):
    """
    Time use guideline filled out by instructors
    
    Based on form in Appendix C (p. 73) of the collective agreement:
    http://www.tssu.ca/wp-content/uploads/2010/01/CA-2004-2010.pdf
    """	
    member = models.ForeignKey(Member, null=False, unique=True)
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
    
    def iterothers(self):
        return (other for key, other in self.config.iteritems() 
                if key.startswith('other')
                and other.get('total',0) > 0)

    others = lambda self:list(self.iterothers())
    
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
hour for each base unit assigned excluding the additional %s B.U. for 
preparation, e.g. %s hours reduction for %s B.U. appointment.''' % (LAB_BONUS, 4, 4+LAB_BONUS)}}
    
    #prep_weekly, set_prep_weekly = getter_setter_2('prep', 'weekly')

    def __unicode__(self):
        return "TA: %s  Base Units: %s" % (self.member.person.userid, self.base_units)
    
    def save(self, newsitem=True, newsitem_author=None, *args, **kwargs):
        for f in self.config:
            # if 'weekly' in False is invalid, so we have to check if self.config[f] is iterable
            # before we check for 'weekly' or 'total' 
            if hasattr(self.config[f], '__iter__'):
                if 'weekly' in self.config[f]:
                    self.config[f]['weekly'] = _round_hours(self.config[f]['weekly'])
                if 'total' in self.config[f]:
                    self.config[f]['total'] = _round_hours(self.config[f]['total'])

        super(TUG, self).save(*args, **kwargs)
        if newsitem:
            n = NewsItem(user=self.member.person, author=newsitem_author, course=self.member.offering,
                    source_app='ta', title='%s Time Use Guideline Changed' % (self.member.offering.name()),
                    content='Your Time Use Guideline for %s has been changed. If you have not already, please review it with the instructor.' % (self.member.offering.name()),
                    url=self.get_absolute_url())
            n.save()

    def expired( self ):
        if self.member.offering.labtut():
            return 'bu' in self.member.config and self.base_units != self.member.bu() - LAB_BONUS_DECIMAL
        else:
            return 'bu' in self.member.config and self.base_units != self.member.bu()
            
    def get_absolute_url(self):
        return reverse('ta.views.view_tug', kwargs={
                'course_slug': self.member.offering.slug, 
                'userid':self.member.person.userid})
    
    def max_hours(self):
        return self.base_units * HOURS_PER_BU

    def total_hours(self):
        """
        Total number of hours assigned
        """
        return sum((decimal.Decimal(data['total']) for _,data in self.iterfielditems() if data['total']))

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
        # 'accounts': default accounts for GTA1, GTA2, UTA, EXT (ra.models.Account.id values)
        # 'start': default start date for contracts ('YYYY-MM-DD')
        # 'end': default end date for contracts ('YYYY-MM-DD')
        # 'deadline': default deadline to accept contracts ('YYYY-MM-DD')
        # 'excluded': courses to exclude from posting (list of Course.id values)
        # 'payperiods': number of pay periods in the semeseter
        # 'contact': contact person for offer questions (Person.id value)
        # 'max_courses': Maximum number of courses an applicant can select
        # 'min_courses': Minimum number of courses an applicant can select
        # 'offer_text': Text to be displayed when students accept/reject the offer (creole markup)
        # 'export_seq': sequence ID for payroll export (so we can create a unique Batch ID)
        # 'extra_questions': additional questions to ask applicants
        # 'instructions': instructions for completing the TA Application
        # 'hide_campuses': whether or not to prompt for Campus

    defaults = {
            'salary': ['0.00']*len(CATEGORY_CHOICES),
            'scholarship': ['0.00']*len(CATEGORY_CHOICES),
            'accounts': [None]*len(CATEGORY_CHOICES),
            'start': '',
            'end': '',
            'deadline': '',
            'excluded': [],
            'bu_defaults': {},
            'payperiods': 8,
            'max_courses': 10,
            'min_courses': 5,
            'contact': None,
            'offer_text': '',
            'export_seq': 0,
            'extra_questions': [],
            'instructions': '',
            'hide_campuses': False
            }
    salary, set_salary = getter_setter('salary')
    scholarship, set_scholarship = getter_setter('scholarship')
    accounts, set_accounts = getter_setter('accounts')
    start, set_start = getter_setter('start')
    end, set_end = getter_setter('end')
    deadline, set_deadline = getter_setter('deadline')
    excluded, set_excluded = getter_setter('excluded')
    bu_defaults, set_bu_defaults = getter_setter('bu_defaults')
    payperiods_str, set_payperiods = getter_setter('payperiods')
    max_courses, set_max_courses = getter_setter('max_courses')
    min_courses, set_min_courses = getter_setter('min_courses')
    offer_text, set_offer_text = getter_setter('offer_text')
    extra_questions, set_extra_questions = getter_setter('extra_questions')
    instructions, set_instructions = getter_setter('instructions')
    hide_campuses, set_hide_campuses = getter_setter('hide_campuses')
    _, set_contact = getter_setter('contact')
    
    class Meta:
        unique_together = (('unit', 'semester'),)
    def __unicode__(self): 
        return "%s, %s" % (self.unit.name, self.semester)
    def save(self, *args, **kwargs):
        super(TAPosting, self).save(*args, **kwargs)
        key = self.html_cache_key()
        cache.delete(key)

    def short_str(self):
        return "%s %s" % (self.unit.label, self.semester)
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."
    
    def contact(self):
        if 'contact' in self.config:
            return Person.objects.get(id=self.config['contact'])
        else:
            return None
    def payperiods(self):
        return decimal.Decimal(self.payperiods_str())
    
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
    
    def is_open(self):
        today = datetime.date.today()
        return self.opens <= today <= self.closes
    
    def next_export_seq(self):
        if 'export_seq' in self.config:
            current = self.config['export_seq']
        else:
            current = 0
        
        self.config['export_seq'] = current + 1
        self.save()
        return self.config['export_seq']
    
    def cat_index(self, val):
        indexer = dict((v[0],k) for k,v in enumerate(CATEGORY_CHOICES))
        return indexer.get(val)
    
    def default_bu(self, offering, count=None):
        """
        Default BUs to assign for this course offering
        """
        strategy = bu_rules.get_bu_strategy( self.semester, self.unit )
        return strategy( self, offering, count )

    def required_bu(self, offering, count=None):
        """
        Actual BUs to assign to this course: default + extra + 0.17*number of TA's
        """
        default = self.default_bu(offering, count=count)
        extra = offering.extra_bu()

        if offering.labtas():
            tacourses = TACourse.objects.filter(contract__posting=self, course=offering).exclude(contract__status__in=['REJ', 'CAN'])
            return default + extra + decimal.Decimal(LAB_BONUS_DECIMAL * len(tacourses)) 
        else:
            return default + extra

    def required_bu_cap(self, offering):
        """
        Actual BUs to assign to this course at its enrolment cap
        """
        default = self.default_bu(offering, offering.enrl_cap)
        extra = offering.extra_bu()
        return default + extra

    def assigned_bu(self, offering):
        """
        BUs already assigned to this course
        """
        total = decimal.Decimal(0)
        tacourses = TACourse.objects.filter(contract__posting=self, course=offering).exclude(contract__status__in=['REJ', 'CAN'])
        if(tacourses.count() > 0):
            total = sum([t.total_bu for t in tacourses])
        return decimal.Decimal(total)

    def applicant_count(self, offering):
        """
        Number of people who have applied to TA this offering
        """
        prefs = CoursePreference.objects.filter(app__posting=self, app__late=False, course=offering.course).exclude(rank=0)
        return prefs.count()
    
    def ta_count(self, offering):
        """
        Number of people who have assigned to be TA for this offering
        """
        tacourses = TACourse.objects.filter(contract__posting=self, course=offering).exclude(contract__status__in=['REJ', 'CAN'])
        return tacourses.count()
    
    def total_pay(self, offering):
        """
        Payments for all tacourses associated with this offering 
        """
        total = 0
        tacourses = TACourse.objects.filter(course=offering, contract__posting=self).exclude(contract__status__in=['REJ', 'CAN'])
        for course in tacourses:
            total += course.pay()
        return total
    
    def all_total(self):
        """
        BU's and Payments for all tacourses associated with all offerings 
        """
        pay = 0
        bus = 0
        tac = TAContract.objects.filter(posting=self).exclude(status__in=['REJ', 'CAN']).count()
        tacourses = TACourse.objects.filter(contract__posting=self).exclude(contract__status__in=['REJ', 'CAN'])
        for course in tacourses:
            pay += course.pay()
            bus += course.total_bu
        return (bus, pay, tac)
    
    def html_cache_key(self):
        return "taposting-offertext-html-" + str(self.id)
    def html_offer_text(self):
        """
        Return the HTML version of this offer's offer_text
        
        Cached to save frequent conversion.
        """
        key = self.html_cache_key()
        html = cache.get(key)
        if html:
            return mark_safe(html)
        else:
            html = text2html(self.offer_text())
            cache.set(key, html, 24*3600) # expires on self.save() above
            return mark_safe(html)
    
        
class Skill(models.Model):
    """
    Skills an applicant specifies in their application.  Skills are specific to a posting.
    """
    posting = models.ForeignKey(TAPosting)
    name = models.CharField(max_length=30)
    position = models.IntegerField()
    
    class Meta:
        ordering = ['position']
        unique_together = (('posting', 'position'))
    def __unicode__(self):
        return "%s in %s" % (self.name, self.posting)



class TAApplication(models.Model):
    """
    TA application filled out by students
    """
    posting = models.ForeignKey(TAPosting)
    person = models.ForeignKey(Person)
    category = models.CharField(max_length=4, blank=False, null=False, choices=CATEGORY_CHOICES, verbose_name='Program')
    current_program = models.CharField(max_length=100, blank=True, null=True, verbose_name="Department",
        help_text='In what department are you a student (e.g. "CMPT", "ENSC", if applicable)?')
    sin = models.CharField(blank=True, max_length=30, verbose_name="SIN",help_text="Social insurance number (required for receiving payments)")
    base_units = models.DecimalField(max_digits=4, decimal_places=2, default=5,
            help_text='Maximum number of base units (BU\'s) you would accept. Each BU represents a maximum of 42 hours of work for the semester. TA appointments can consist of 2 to 5 base units and are based on course enrollments and department requirements.')
    experience =  models.TextField(blank=True, null=True,
        verbose_name="Additional Experience",
        help_text='Describe any other experience that you think may be relevant to these courses.')
    course_load = models.TextField(blank=True, verbose_name="Intended course load",
        help_text='Describe the intended course load of the semester being applied for.')
    other_support = models.TextField(blank=True, null=True,
        verbose_name="Other financial support",
        help_text='Describe any other funding you expect to receive this semester (grad students only).')
    comments = models.TextField(verbose_name="Additional comments", blank=True, null=True)
    rank = models.IntegerField(blank=False, default=0) 
    late = models.BooleanField(blank=False, default=False)
    admin_created = models.BooleanField(blank=False, default=False)
    config = JSONField(null=False, blank=False, default={})
        # 'extra_questions' - a dictionary of answers to extra questions. {'How do you feel?': 'Pretty sharp.'} 
 
    class Meta:
        unique_together = (('person', 'posting'),)
    def __unicode__(self):
        return "%s  Posting: %s" % (self.person, self.posting)
    
    def course_pref_display(self):
        crs = []
        cps = self.coursepreference_set.exclude(rank=0).order_by('rank').select_related('course')
        for cp in cps:
            crs.append(cp.course.subject + ' ' + cp.course.number)
        return ', '.join(crs)
    
    def course_assigned_display(self):
        crs = []
        tacrss = TACourse.objects.filter(contract__application=self).select_related('course')
        for tacrs in tacrss:
            crs.append(tacrs.course.subject + ' ' + tacrs.course.number)
        return ', '.join(crs)
    
    def base_units_assigned(self):
        crs = TACourse.objects.filter(contract__application=self).aggregate(Sum('bu'))
        return crs['bu__sum']

PREFERENCE_CHOICES = (
        ('PRF', 'Preferred'),
        ('WIL', 'Willing'),
        ('NOT', 'Not willing'),
)
PREFERENCES = dict(PREFERENCE_CHOICES)

class CampusPreference(models.Model):
    """
    Preference ranking for a campuses
    """
    app = models.ForeignKey(TAApplication)
    campus = models.CharField(max_length=5, choices=CAMPUS_CHOICES)
    pref = models.CharField(max_length=3, choices=PREFERENCE_CHOICES)
    class Meta:
        unique_together = (('app', 'campus'),)

LEVEL_CHOICES = (
    ('EXPR', 'Expert'),
    ('GOOD', 'Good'),
    ('SOME', 'Some'),
    ('NONE', 'None'),
)
LEVELS = dict(LEVEL_CHOICES)
class SkillLevel(models.Model):
    """
    Skill of an applicant
    """
    skill = models.ForeignKey(Skill)
    app = models.ForeignKey(TAApplication)
    level = models.CharField(max_length=4, choices=LEVEL_CHOICES)
    #class Meta:
    #    unique_together = (('app', 'skill'),)


APPOINTMENT_CHOICES = (
        ("INIT","Initial appointment to this position"),
        ("REAP","Reappointment to same position or revision to appointment"),       
    )
STATUS_CHOICES = (
        ("NEW","Draft"), # not yet sent to TA
        ("OPN","Offered"), # offer made, but not accepted/rejected/cancelled
        ("REJ","Rejected"), 
        ("ACC","Accepted"),
        ("SGN","Contract Signed"), # after accepted and manager has signed contract
        ("CAN","Cancelled"),
    )
STATUS = dict(STATUS_CHOICES)
STATUSES_NOT_TAING = ['NEW', 'REJ', 'CAN'] # statuses that mean "not actually TAing"

class TAContract(models.Model):
    """    
    TA Contract, filled in by TAAD
    """
    status  = models.CharField(max_length=3, choices=STATUS_CHOICES, verbose_name="Appointment Status", default="NEW")
    posting = models.ForeignKey(TAPosting)
    application = models.ForeignKey(TAApplication)
    sin = models.CharField(max_length=30, verbose_name="SIN",help_text="Social insurance number")
    pay_start = models.DateField()
    pay_end = models.DateField()
    appt_category = models.CharField(max_length=4, choices=CATEGORY_CHOICES, verbose_name="Appointment Category", default="GTA1")
    position_number = models.ForeignKey(Account)
    appt = models.CharField(max_length=4, choices=APPOINTMENT_CHOICES, verbose_name="Appointment", default="INIT")
    pay_per_bu = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Pay per Base Unit Semester Rate.",)
    scholarship_per_bu = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Scholarship per Base Unit Semester Rate.",)
    appt_cond = models.BooleanField(default=False, verbose_name="Conditional")
    appt_tssu = models.BooleanField(default=True, verbose_name="Appointment in TSSU")
    deadline = models.DateField(verbose_name="Acceptance Deadline", help_text='Deadline for the applicant to accept/decline the offer')
    remarks = models.TextField(blank=True)
    
    created_by = models.CharField(max_length=8, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = (('posting', 'application'),)
        
    def __unicode__(self):
        return "%s" % (self.application.person)

    def save(self, *args, **kwargs):
        super(TAContract, self).save(*args, **kwargs)

        # set SIN field on any GradStudent objects for this person
        from grad.models import GradStudent
        for gs in GradStudent.objects.filter(person=self.application.person):
            dummy_sins = ['999999999', '000000000', '123456789']
            if (('sin' not in gs.config 
                or ('sin' in gs.config and gs.config['sin'] in dummy_sins)) 
                and not self.sin in dummy_sins ):
                gs.person.set_sin(self.sin)
                gs.person.save()

        # if signed, create the Member objects so they have access to the courses.
        courses = TACourse.objects.filter(contract=self)
        for crs in courses:
            members = Member.objects.filter(person=self.application.person, offering=crs.course).exclude(role='DROP')
            # assert( len(members) <= 1 )
            dropped_members = Member.objects.filter(person=self.application.person, offering=crs.course, role='DROP')
            # Should Member just have an optional FK to TACourse rather than getting a copy of the BU? 
            if (self.status in ['SGN', 'ACC'] and crs.bu > 0) and not members:
                if dropped_members:
                    m = dropped_members[0]
                    # if this student was added/dropped by the prof, then added_reason might not be CTA
                    m.added_reason='CTA'
                    m.role = "TA"
                else:
                    # signed, but not a member: create
                    m = Member(person=self.application.person, offering=crs.course, role='TA',
                           added_reason='CTA', credits=0, career='NONS')
                m.config['bu'] = crs.total_bu
                m.save()
            elif (self.status in ['SGN', 'ACC'] and crs.bu > 0 ) and members:
                # change in BU -> change in BU for Member
                m = members[0]
                if not 'bu' in m.config or m.config['bu'] != crs.total_bu:
                    # if this student was added by the prof, then added_reason might not be CTA
                    m.config['bu'] = crs.total_bu
                    m.added_reason='CTA'
                    m.save()
            elif ( (not self.status in ['SGN', 'ACC']) or crs.bu == 0) and members:
                # already in course, but status isn't signed: remove
                m = members[0]
                if m.role == 'TA' and m.added_reason == 'CTA':
                    m.role = 'DROP'
                    m.save()
            else: 
                # (self.status not in ['SGN', 'ACC'] or crs.bu == 0) and not members
                # there is no contract and this student doesn't exist as a Member in the course
                pass
            
            if self.status in ('CAN', 'REJ'):
                # These students should be removed from their courses. 
                crs.bu = 0
                crs.save()

            # If this course has 0 BUs and a course Member record, clear that record. 
            if crs.bu == 0 and members:
                m = members[0]
                if m.role == 'TA' and m.added_reason == 'CTA':
                    m.role = 'DROP'
                    m.save()

        # If they are CTA-added members of any other course this semester, they probably shouldn't be
        members = Member.objects.filter(person=self.application.person, role='TA', added_reason='CTA', offering__semester=self.posting.semester )
        courseofferings = [crs.course for crs in courses if crs.bu > 0]
        for member in members:
            if member.offering not in courseofferings:
                member.role = 'DROP'
                member.save()


    def first_assign(self, application, posting):
        self.application = application
        self.posting = posting
        self.sin = application.sin
        self.appt_category = application.category
        self.pay_start = posting.start()
        self.pay_end = posting.end()
        self.deadline = posting.deadline()
        index = posting.cat_index(application.category)
        self.position_number = Account.objects.get(pk=posting.accounts()[index])
        self.pay_per_bu = posting.salary()[index]
        self.scholarship_per_bu = posting.scholarship()[index]
        self.save()

    def bu(self):
        courses = TACourse.objects.filter(contract=self)
        return sum( [course.bu for course in courses] )

    def total_bu(self):
        courses = TACourse.objects.filter(contract=self)
        if self.status in ('CAN', 'REJ'):
            return 0
        return sum( [course.total_bu for course in courses] )

    def prep_bu(self):
        courses = TACourse.objects.filter(contract=self)
        return sum( [course.prep_bu for course in courses] )


class CourseDescription(models.Model):
    """
    Description of the work for a TA contract
    """
    unit = models.ForeignKey(Unit)
    description = models.CharField(max_length=60, blank=False, null=False, help_text="Description of the work for a course, as it will appear on the contract. (e.g. 'Office/marking')")
    labtut = models.BooleanField(default=False, verbose_name="Lab/Tutorial?", help_text="Does this description get the %s BU bonus?"%(LAB_BONUS))
    hidden = models.BooleanField(default=False)
    config = JSONField(null=False, blank=False, default={})
    
    def __unicode__(self):
        return self.description


class TACourse(models.Model):
    course = models.ForeignKey(CourseOffering, blank=False, null=False)
    contract = models.ForeignKey(TAContract, blank=False, null=False)
    description = models.ForeignKey(CourseDescription, blank=False, null=False)
    bu = models.DecimalField(max_digits=4, decimal_places=2)
    
    class Meta:
        unique_together = (('contract', 'course'),)
    
    def __unicode__(self):
        return "Course: %s  TA: %s" % (self.course, self.contract)

    @property
    def prep_bu(self):
        """
        Return the prep BUs for this assignment
        """
        if self.has_labtut():
            return LAB_BONUS_DECIMAL
        else:
            return 0

    @property
    def total_bu(self):
        """
        Return the total BUs for this assignment
        """
        return self.bu + self.prep_bu

    def has_labtut(self):
        """
        Does this assignment deserve the LAB_BONUS bonus?
        """
        return self.description.labtut
    
    def default_description(self):
        """
        Guess an appropriate CourseDescription object for this contract. Must have self.course filled in first.
        """
        labta = self.course.labtas()
        descs = CourseDescription.objects.filter(unit=self.contract.posting.unit, hidden=False, labtut=labta)
        if descs:
            return descs[0]
        else:
            raise ValueError, "No appropriate CourseDescription found"
    
    def pay(self):
        contract = self.contract
        if contract.status in STATUSES_NOT_TAING:
            return decimal.Decimal(0)
        total = self.total_bu * contract.pay_per_bu
        total += self.bu * contract.scholarship_per_bu
        return total
        
TAKEN_CHOICES = (
        ('YES', 'Yes: this course at SFU'),
        ('SIM', 'Yes: a similar course elsewhere'),
        ('KNO', 'No, but I know the course material'),
        ('NO', 'No, I don\'t know the material well'),
        )
EXPER_CHOICES = (
        ('FAM', 'Very familiar with course material'),
        ('SOM', 'Somewhat familiar with course material'),
        ('NOT', 'Not familiar with course material'),
        )
    
class CoursePreference(models.Model):
    app = models.ForeignKey(TAApplication)
    course = models.ForeignKey(Course)
    taken = models.CharField(max_length=3, choices=TAKEN_CHOICES, blank=False, null=False)
    exper = models.CharField(max_length=3, choices=EXPER_CHOICES, blank=False, null=False, verbose_name="Experience")
    rank = models.IntegerField(blank=False)
    #class Meta:
    #    unique_together = (('app', 'course'),)

    def __unicode__(self):
        if self.app_id and self.course_id:
            return "%s's pref for %s" % (self.app.person, self.course)
        else:
            return "new CoursePreference"
