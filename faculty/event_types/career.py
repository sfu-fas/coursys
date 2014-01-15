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

class AppointmentEventType(CareerEventType):
    class EntryForm(BaseEntryForm):
        spousal_hire = forms.BooleanField(initial=False)
