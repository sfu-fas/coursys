from django.db import models
from coredata.models import Person, Unit, Semester
from jsonfield import JSONField
#from courselib.json_fields import getter_setter
from autoslug import AutoSlugField
from courselib.slugs import make_slug
from grad.models import Scholarship
from pages.models import _normalize_newlines

HIRING_CATEGORY_CHOICES = (
    ('U', 'Undergrad'),
    ('E', 'Grad Employee'),
    ('N', 'Non-Student'),
    ('S', 'Grad Scholarship'),
    )
    
#PAY_TYPE_CHOICES = (
#    ('H', 'Hourly'),
#    ('B', 'Biweekly'),
#    ('L', 'Lump Sum'),
#    )

PAY_FREQUENCY_CHOICES = (
    ('B', 'Biweekly'),
    ('L', 'Lump Sum'),
)

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
    
    class Meta:
        ordering = ['project_number']

    def __unicode__(self):
        return "%06i (%s)" % (self.project_number, self.fund_number)
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."

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

    class Meta:
        ordering = ['account_number']

    def __unicode__(self):
        return "%06i (%s)" % (self.account_number, self.title)
    def delete(self, *args, **kwargs):
        raise NotImplementedError, "This object cannot be deleted because it is used as a foreign key."


DEFAULT_LETTER = [
        """This is to confirm remuneration of work performed as a Research Assistant from %(start_date)s to %(end_date)s, will be a Lump Sum payment of $%(lump_sum_pay)s.""",
        """Termination of this appointment may be initiated by either party giving one (1) week notice, except in the case of termination for cause.""",
        """This contract of employment exists solely between myself as recipient of research grant funds and your self. In no manner of form does this employment relationship extend to or affect Simon Fraser University in any way.""",
        """The primary purpose of this appointment is to assist you in furthering your education and the pursuit of your degree through the performance of research activities in your field of study. As such, payment for these activities will be classified as scholarship income for taxation purposes. Accordingly, there will be no income tax, CPP or EI deductions from income. You should set aside funds to cover your eventual income tax obligation; note that the first $3K total annual income from scholarship sources is not taxable.""",
        """Basic Benefits: further details are in SFU Policies and Procedures R 50.02, which can be found on the SFU website.""",
        """If you accept the terms of this appointment, please sign and return the enclosed copy of this letter, retaining the original for your records.""",
    ]


class RAAppointment(models.Model):
    """
    This stores information about a (Research Assistant)s application and pay.
    """
    person = models.ForeignKey(Person, help_text='The RA who is being appointed.', null=False, blank=False, related_name='ra_person')
    sin = models.PositiveIntegerField()
    hiring_faculty = models.ForeignKey(Person, help_text='The manager who is hiring the RA.', related_name='ra_hiring_faculty')
    unit = models.ForeignKey(Unit, help_text='The unit that owns the appointment', null=False, blank=False)
    hiring_category = models.CharField(max_length=60, choices=HIRING_CATEGORY_CHOICES, default='S')
    scholarship = models.ForeignKey(Scholarship, null=True, blank=True, help_text='Scholarship associated with this appointment. Optional.')
    project = models.ForeignKey(Project, null=False, blank=False)
    account = models.ForeignKey(Account, null=False, blank=False)
    start_date = models.DateField(auto_now=False, auto_now_add=False)
    end_date = models.DateField(auto_now=False, auto_now_add=False)
    pay_frequency = models.CharField(max_length=60, choices=PAY_FREQUENCY_CHOICES, default='B')
    lump_sum_pay = models.DecimalField(max_digits=8, decimal_places=2, verbose_name="Total Pay")
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
    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff
    

    def __unicode__(self):
        return unicode(self.person) + "@" + unicode(self.created_at)

    class Meta:
        ordering = ['person', 'created_at']
    
    def default_letter_text(self):
        """
        Default text for the letter (for editing, or use if not set)
        """
        substitutions = {
            'start_date': self.start_date.strftime("%B %d, %Y"),
            'end_date': self.end_date.strftime("%B %d, %Y"),
            'lump_sum_pay': self.lump_sum_pay,
            }
        return '\n\n'.join(DEFAULT_LETTER) % substitutions
    
    def letter_paragraphs(self):
        """
        Return list of paragraphs in the letter (for PDF creation)
        """
        text = self.offer_letter_text or self.default_letter_text()
        text = _normalize_newlines(text)
        return text.split("\n\n") 
    
    def start_semester(self):
        "Guess the starting semester of this appointment"
        return Semester.get_semester(self.start_date)
    def end_semester(self):
        "Guess the ending semester of this appointment"
        return Semester.get_semester(self.end_date)
    def semester_length(self):
        "The number of semesters this contracts lasts for"
        return self.end_semester() - self.start_semester() + 1
