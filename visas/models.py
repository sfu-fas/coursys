from django.db import models
from coredata.models import VISA_STATUSES, Person
from django.utils import timezone
from django import forms
from courselib.json_fields import JSONField
from coredata.widgets import CalendarWidget, PersonField

# Create your models here.


class Visa (models.Model):
    person = models.ForeignKey(Person, null=False, blank=False)
    status = forms.MultipleChoiceField(VISA_STATUSES, required=True)
    start_date = models.DateField('Start Date', default=timezone.now().date())
    end_date = models.DateField('End Date', blank=True)
    config = JSONField(null=False, blank=False, editable=False, default={})  # For future fields
    hidden = models.BooleanField(default=False, editable=False)


class VisaForm(forms.ModelForm):
    status = forms.MultipleChoiceField(VISA_STATUSES, required=True)

    class Meta:
        exclude = []
        model = Visa
        person = PersonField()
        widgets = {
                   'start_date': CalendarWidget,
                   'end_date': CalendarWidget
                  }