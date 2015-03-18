from django.db import models
from coredata.models import VISA_STATUSES, Person
from django.utils import timezone
from django import forms
from courselib.json_fields import JSONField
from coredata.widgets import CalendarWidget, PersonField
from coredata.models import Semester


EXPIRY_STATUSES = ['Expired', 'Expiring Soon', 'Valid']


class Visa (models.Model):
    person = models.ForeignKey(Person, null=False, blank=False)
    status = models.CharField(max_length=50, choices=VISA_STATUSES, default='')
    start_date = models.DateField('Start Date', default=timezone.now().date())
    end_date = models.DateField('End Date', blank=True)
    config = JSONField(null=False, blank=False, editable=False, default={})  # For future fields
    hidden = models.BooleanField(default=False, editable=False)

    # Helper methods to display a proper status we can sort on
    def is_valid(self):
        return self.start_date <= timezone.now().date() < self.end_date

    def is_expired(self):
        return timezone.now().date() > self.end_date

    # If this visa will expire this semester, that may be important
    # A better business rule may be forthcoming.
    def is_almost_expired(self):
        current = Semester.current()
        return (self.is_valid()) and (self.end_date < current.end)

    def get_validity(self):
        if self.is_expired():
            return EXPIRY_STATUSES[0]
        if self.is_almost_expired():
            return EXPIRY_STATUSES[1]
        if self.is_valid():
            return EXPIRY_STATUSES[2]
        return "Unknown"  # Should be impossible, but defaulting to Valid is just wrong.

    def __unicode__(self):
        return "%s, %s, %s" % (self.person, self.status, self.start_date)


class VisaForm(forms.ModelForm):
    class Meta:
        exclude = []
        model = Visa
        person = PersonField()
        widgets = {
            'start_date': CalendarWidget,
            'end_date': CalendarWidget
            }