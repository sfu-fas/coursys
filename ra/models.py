from django.db import models
from coredata.models import Person, Unit, Semester
from jsonfield import JSONField
from courselib.json_fields import getter_setter
from autoslug import AutoSlugField
from courselib.slugs import make_slug
from grad.models import Scholarship
from pages.models import _normalize_newlines
import datetime

HIRING_CATEGORY_CHOICES = (
    ('U', 'Undergrad'),
    ('E', 'Grad Employee'),
    ('N', 'Non-Student'),
    ('S', 'Grad Scholarship'),
    ('RA', 'Research Assistant'),
    ('RSS', 'Research Services Staff'),
    ('PDF', 'Post Doctoral Fellow'),
    ('ONC', 'Other Non Continuing'),
    ('RA2', 'University Research Assistant (Min of 2 years with Benefits)'),
    ('RAR', 'University Research Assistant (Renewal after 2 years with Benefits)'),
    ('GRA', 'Graduate Research Assistant'),
    ('NS', 'National Scholarship'),
    )
HIRING_CATEGORY_DISABLED = set(['U','E','N','S']) # hiring categories that cannot be selected for new contracts


#PAY_TYPE_CHOICES = (
#    ('H', 'Hourly'),
#    ('B', 'Biweekly'),
#    ('L', 'Lump Sum'),
#    )

PAY_FREQUENCY_CHOICES = (
    ('B', 'Biweekly'),
    ('L', 'Lump Sum'),
)

# If a RA is within SEMESTER_SLIDE days of the border
# of a semester, it is pushed into that semester.
# This is to prevent RAs that are, for example, 2 days into
# the Summer semester from being split into two equal-pay
# chunks. 
SEMESTER_SLIDE = 15

class Project(models.Model):
    """
    A table to look up the appropriate fund number based on the project number
    """
    unit = models.ForeignKey(Unit, null=False, blank=False)
    project_number = models.PositiveIntegerField()
    fund_number = models.PositiveIntegerField()
    def autoslug(self):
        return make_slug(self.unit.label + '-' + unicode(self.project_number))
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)
    hidden = models.BooleanField(null=False, default=False)
    
    class Meta:
        ordering = ['project_number']

    def __unicode__(self):
        return "%06i (%s)" % (self.project_number, self.fund_number)
    def delete(self, *args, **kwargs):
        self.hidden = True
        self.save()

class Account(models.Model):
    """
    A table to look up the appropriate position number based on the account number.
    """
    unit = models.ForeignKey(Unit, null=False, blank=False)
    account_number = models.PositiveIntegerField()
    position_number = models.PositiveIntegerField()
    title = models.CharField(max_length=60)
    def autoslug(self):
        return make_slug(self.unit.label + '-' + unicode(self.account_number) + '-' + unicode(self.title))
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)
    hidden = models.BooleanField(null=False, default=False)

    class Meta:
        ordering = ['account_number']

    def __unicode__(self):
        return "%06i (%s)" % (self.account_number, self.title)
    def delete(self, *args, **kwargs):
        self.hidden = True
        self.save()


DEFAULT_LETTER = [
        """Termination of this appointment may be initiated by either party giving one (1) week notice, except in the case of termination for cause.""",
        """This contract of employment exists solely between myself as recipient of research grant funds and your self. In no manner of form does this employment relationship extend to or affect Simon Fraser University in any way.""",
        """The primary purpose of this appointment is to assist you in furthering your education and the pursuit of your degree through the performance of research activities in your field of study. As such, payment for these activities will be classified as scholarship income for taxation purposes. Accordingly, there will be no income tax, CPP or EI deductions from income. You should set aside funds to cover your eventual income tax obligation; note that the first $3K total annual income from scholarship sources is not taxable.""",
        """Basic Benefits: further details are in SFU Policies and Procedures R 50.02, which can be found on the SFU website.""",
        """Hours of work: There will be a great deal of flexibility exercised in the time and place of the performance of these services, but I expect these hours not to exceed 40 hours per week.""",
        """If you accept the terms of this appointment, please sign and return the enclosed copy of this letter, retaining the original for your records.""",
    ]
DEFAULT_LETTER_LUMPSUM = ["""This is to confirm remuneration of work performed as a Research Assistant from %(start_date)s to %(end_date)s, will be a Lump Sum payment of $%(lump_sum_pay)s."""] \
                         + DEFAULT_LETTER
DEFAULT_LETTER_BIWEEKLY = ["""This is to confirm remuneration of work performed as a Research Assistant from %(start_date)s to %(end_date)s. The remuneration will be a biweekly payment of $%(biweekly_pay)s for a total amount of $%(lump_sum_pay)s inclusive of 4%% vacation."""] \
                         + DEFAULT_LETTER

class RAAppointment(models.Model):
    """
    This stores information about a (Research Assistant)s application and pay.
    """
    person = models.ForeignKey(Person, help_text='The RA who is being appointed.', null=False, blank=False, related_name='ra_person')
    sin = models.PositiveIntegerField(null=True, blank=True)
    hiring_faculty = models.ForeignKey(Person, help_text='The manager who is hiring the RA.', related_name='ra_hiring_faculty')
    unit = models.ForeignKey(Unit, help_text='The unit that owns the appointment', null=False, blank=False)
    hiring_category = models.CharField(max_length=60, choices=HIRING_CATEGORY_CHOICES, default='GRA')
    scholarship = models.ForeignKey(Scholarship, null=True, blank=True, help_text='Scholarship associated with this appointment. Optional.')
    project = models.ForeignKey(Project, null=False, blank=False)
    account = models.ForeignKey(Account, null=False, blank=False)
    start_date = models.DateField(auto_now=False, auto_now_add=False)
    end_date = models.DateField(auto_now=False, auto_now_add=False)
    pay_frequency = models.CharField(max_length=60, choices=PAY_FREQUENCY_CHOICES, default='B')
    lump_sum_pay = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Total Pay")
    lump_sum_hours = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Total Hours")
    biweekly_pay = models.DecimalField(max_digits=8, decimal_places=2)
    pay_periods = models.DecimalField(max_digits=6, decimal_places=1)
    hourly_pay = models.DecimalField(max_digits=8, decimal_places=2)
    hours = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Biweekly Hours")
    reappointment = models.BooleanField(default=False, help_text="Are we re-appointing to the same position?")
    medical_benefits = models.BooleanField(default=False, help_text="50% of Medical Service Plan")
    dental_benefits = models.BooleanField(default=False, help_text="50% of Dental Plan")
    notes = models.TextField(blank=True, help_text="Biweekly emplyment earnings rates must include vacation pay, hourly rates will automatically have vacation pay added. The employer cost of statutory benefits will be charged to the amount to the earnings rate.");
    comments = models.TextField(blank=True, help_text="For internal use")
    offer_letter_text = models.TextField(null=True, help_text="Text of the offer letter to be signed by the RA and supervisor.")
    def autoslug(self):
        if self.person.userid:
            ident = self.person.userid
        else:
            ident = unicode(self.person.emplid)
        return make_slug(self.unit.label + '-' + unicode(self.start_date.year) + '-' + ident)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    deleted = models.BooleanField(null=False, default=False)
    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff
    defaults = {'use_hourly': False}
    use_hourly, set_use_hourly = getter_setter('use_hourly')

    def __unicode__(self):
        return unicode(self.person) + "@" + unicode(self.created_at)

    class Meta:
        ordering = ['person', 'created_at']

    def save(self, *args, **kwargs):
        # set SIN field on the Person object
        if self.sin and 'sin' not in self.person.config:
            self.person.set_sin(self.sin)
            self.person.save()
        super(RAAppointment, self).save(*args, **kwargs)
    
    def default_letter_text(self):
        """
        Default text for the letter (for editing, or use if not set)
        """
        substitutions = {
            'start_date': self.start_date.strftime("%B %d, %Y"),
            'end_date': self.end_date.strftime("%B %d, %Y"),
            'lump_sum_pay': self.lump_sum_pay,
            'biweekly_pay': self.biweekly_pay,
            }
        if self.pay_frequency == 'B':
            text = DEFAULT_LETTER_BIWEEKLY
        else:
            text = DEFAULT_LETTER_LUMPSUM
        return '\n\n'.join(text) % substitutions
    
    def letter_paragraphs(self):
        """
        Return list of paragraphs in the letter (for PDF creation)
        """
        text = self.offer_letter_text or self.default_letter_text()
        text = _normalize_newlines(text)
        return text.split("\n\n") 
    
    @classmethod
    def semester_guess(cls, date):
        """
        Guess the semester for a date, in the way that financial people do (without regard to class start/end dates)
        """
        mo = date.month
        if mo <= 4:
            se = 1
        elif mo <= 8:
            se = 4
        else:
            se = 7
        semname = str((date.year-1900)*10 + se)
        return Semester.objects.get(name=semname)

    @classmethod
    def start_end_dates(cls, semester):
        """
        First and last days of the semester, in the way that financial people do (without regard to class start/end dates)
        """
        yr = int(semester.name[0:3]) + 1900
        sm = int(semester.name[3])
        if sm == 1:
            start = datetime.date(yr, 1, 1)
            end = datetime.date(yr, 4, 30)
        elif sm == 4:
            start = datetime.date(yr, 5, 1)
            end = datetime.date(yr, 8, 31)
        elif sm == 7:
            start = datetime.date(yr, 9, 1)
            end = datetime.date(yr, 12, 31)
        return start, end
        
    def start_semester(self):
        "Guess the starting semester of this appointment"
        start_semester = RAAppointment.semester_guess(self.start_date)
        # We do this to eliminate hang - if you're starting N days before 
        # semester 1134, you aren't splitting that payment across 2 semesters. 
        start, end = RAAppointment.start_end_dates(start_semester)
        if end - self.start_date < datetime.timedelta(SEMESTER_SLIDE):
            return start_semester.next_semester()
        return start_semester

    def end_semester(self):
        "Guess the ending semester of this appointment"
        end_semester = RAAppointment.semester_guess(self.end_date)
        # We do this to eliminate hang - if you're starting N days after 
        # semester 1134, you aren't splitting that payment across 2 semesters. 
        start, end = RAAppointment.start_end_dates(end_semester)
        if self.end_date - start < datetime.timedelta(SEMESTER_SLIDE):
            return end_semester.previous_semester()
        return end_semester

    def semester_length(self):
        "The number of semesters this contracts lasts for"
        return self.end_semester() - self.start_semester() + 1



class SemesterConfig(models.Model):
    """
    A table for department-specific semester config.
    """
    unit = models.ForeignKey(Unit, null=False, blank=False)
    semester = models.ForeignKey(Semester, null=False, blank=False)
    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff
    defaults = {'start_date': None, 'end_date': None}
    # 'start_date': default first day of contracts that semester, 'YYYY-MM-DD'
    # 'end_date': default last day of contracts that semester, 'YYYY-MM-DD'
    
    class Meta:
        unique_together = (('unit', 'semester'),)
    
    @classmethod
    def get_config(cls, units, semester):
        """
        Either get existing SemesterConfig or return a new one.
        """
        configs = SemesterConfig.objects.filter(unit__in=units, semester=semester).select_related('semester')
        if configs:
            return configs[0]
        else:
            return SemesterConfig(unit=list(units)[0], semester=semester)
    
    def start_date(self):
        if 'start_date'in self.config:
            return datetime.datetime.strptime(self.config['start_date'], '%Y-%m-%d').date()
        else:
            return self.semester.start

    def end_date(self):
        if 'end_date'in self.config:
            return datetime.datetime.strptime(self.config['end_date'], '%Y-%m-%d').date()
        else:
            return self.semester.end

    def set_start_date(self, date):
        self.config['start_date'] = date.strftime('%Y-%m-%d')

    def set_end_date(self, date):
        self.config['end_date'] = date.strftime('%Y-%m-%d')


