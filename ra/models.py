from django.db import models
from coredata.models import Person
from django.forms.models import ModelForm

HIRING_CATEGORY_CHOICES = (
    ('S', 'Scholarship'),
    # TODO: populate hiring category choices.
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
    
    project_number = models.PositiveIntegerField()
    fund_number = models.PositiveIntegerField()

    def __unicode__(self):
        return unicode(self.project_number)

class Account(models.Model):
    """
    A table to look up the appropriate position number based on the account number.
    """
    
    account_number = models.PositiveIntegerField()
    position_number = models.PositiveIntegerField()

    def __unicode__(self):
        return unicode(self.account_number)

class RAAppointment(models.Model):
    """
    This stores information about a (Research Assistant)s application and pay.
    """

    
    person = models.ForeignKey(Person, help_text='The RA who is being appointed.', null=False, blank=False, related_name='ra_person')
    hiring_faculty = models.ForeignKey(Person, help_text='The manager who is hiring the RA.', related_name='ra_hiring_faculty')
    hiring_category = models.CharField(max_length=60, choices=HIRING_CATEGORY_CHOICES)
    #hiring_department = models.ForeignKey()
    project = models.ForeignKey(Project, null=False, blank=False)
    account = models.ForeignKey(Account, null=False, blank=False)
    start_date = models.DateField(auto_now=False, auto_now_add=False)
    end_date = models.DateField(auto_now=False, auto_now_add=False)
    pay_type = models.CharField(max_length=60, choices=PAY_TYPE_CHOICES)
    # The amount paid hourly, biweekly, or as a lump sum.
    pay_amount = models.DecimalField(max_digits=6, decimal_places=2)
    employment_hours = models.PositiveSmallIntegerField()
    employment_minutes = models.PositiveSmallIntegerField()
    units = models.DecimalField(max_digits=6, decimal_places=3)
    reappointment = models.BooleanField(default=False)
    medical_benefits = models.BooleanField(default=False)
    dental_benefits = models.BooleanField(default=False)
    notes = models.TextField();
    comments = models.TextField();
    created_at = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return unicode(self.person) + "@" + unicode(self.created_at)

    class Meta:
        ordering = ['person', 'created_at']