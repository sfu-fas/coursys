# career-level event types: appointment, salary

from base import CareerEventType, BaseEntryForm
from django import forms

RANK_CHOICES = [
        ('LECT', 'Lecturer'),
        ('SLET', 'Senior Lecturer'),
        ('ASSI', 'Assistant Professor'),
        ('ASSO', 'Associate Professor'),
        ('FULL', 'Full Professor'),
        ]
LEAVING_CHOICES = [
        ('HERE', u'\u2014'), # hasn't left yet
        ('RETI', 'Retired'),
        ('END', 'Limited-term contract ended'),
        ('UNIV', 'Left: job at another University'),
        ('PRIV', 'Left: private-sector job'),
        ('GONE', 'Left: employent status unknown'),
        ('DIED', 'Deceased'),
        ('OTHR', 'Other/Unknown'),
        ]


class AppointmentEventType(CareerEventType):
    class EntryForm(BaseEntryForm):
        spousal_hire = forms.BooleanField(initial=False)
        leaving_reason = forms.ChoiceField(initial='HERE', choices=LEAVING_CHOICES)
