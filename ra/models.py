from django.db import models
from coredata.models import Person, Unit
from jsonfield import JSONField
from courselib.json_fields import getter_setter
from autoslug import AutoSlugField
from courselib.slugs import make_slug
from grad.models import Scholarship

HIRING_CATEGORY_CHOICES = (
    ('U', 'Undergrad'),
    ('E', 'Employee'),
    ('N', 'None'),
    ('S', 'Scholarship'),
    )
    
PAY_TYPE_CHOICES = (
    ('H', 'Hourly'),
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

    def __unicode__(self):
        return unicode(self.project_number)

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

    def __unicode__(self):
        return unicode(self.account_number)

class RAAppointment(models.Model):
    """
    This stores information about a (Research Assistant)s application and pay.
    """
    person = models.ForeignKey(Person, help_text='The RA who is being appointed.', null=False, blank=False, related_name='ra_person')
    sin = models.PositiveIntegerField()
    hiring_faculty = models.ForeignKey(Person, help_text='The manager who is hiring the RA.', related_name='ra_hiring_faculty')
    unit = models.ForeignKey(Unit, help_text='The unit that owns the appointment', null=False, blank=False)
    hiring_category = models.CharField(max_length=60, choices=HIRING_CATEGORY_CHOICES)
    #hiring_department = models.ForeignKey()
    scholarship = models.ForeignKey(Scholarship, null=True, blank=True, help_text='Optional.')
    project = models.ForeignKey(Project, null=False, blank=False)
    account = models.ForeignKey(Account, null=False, blank=False)
    start_date = models.DateField(auto_now=False, auto_now_add=False)
    end_date = models.DateField(auto_now=False, auto_now_add=False)
    lump_sum_pay = models.DecimalField(max_digits=6, decimal_places=2)
    biweekly_pay = models.DecimalField(max_digits=6, decimal_places=2)
    pay_periods = models.DecimalField(max_digits=6, decimal_places=3)
    hourly_pay = models.DecimalField(max_digits=6, decimal_places=2)
    hours = models.PositiveSmallIntegerField()
    # pay_period = models.CharField(max_length=60, choices=PAY_TYPE_CHOICES)
    # # The amount paid hourly, biweekly, or as a lump sum.
    # pay_amount = models.DecimalField(max_digits=6, decimal_places=2, help_text="The amount paid either hourly, biweekly, or in a lump sum.")
    # employment_hours = models.PositiveSmallIntegerField()
    # employment_minutes = models.PositiveSmallIntegerField()
    # units = models.DecimalField(max_digits=6, decimal_places=3)
    reappointment = models.BooleanField(default=False, help_text="Are we re-appointing to the same position?")
    medical_benefits = models.BooleanField(default=False, help_text="50% of Medical Service Plan")
    dental_benefits = models.BooleanField(default=False, help_text="50% of Dental Plan")
    notes = models.TextField(blank=True, help_text="Biweekly emplyment earnings rates must include vacation pay, hourly rates will automatically have vacation pay added. The employer cost of statutory benefits will be charged to the amount to the earnings rate.");
    comments = models.TextField(blank=True, help_text="For internal use");
    def autoslug(self):
        return make_slug(self.unit.label + '-' + unicode(self.start_date.year) + '-' + self.person.userid)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff
    

    def __unicode__(self):
        return unicode(self.person) + "@" + unicode(self.created_at)

    class Meta:
        ordering = ['person', 'created_at']