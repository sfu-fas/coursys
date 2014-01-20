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
        ('GONE', 'Left: employment status unknown'),
        ('DIED', 'Deceased'),
        ('OTHR', 'Other/Unknown'),
        ]


class AppointmentEventType(CareerEventType):
    """
    The big career event: from hiring to leaving the position.
    """
    class EntryForm(BaseEntryForm):
        spousal_hire = forms.BooleanField(initial=False)
        leaving_reason = forms.ChoiceField(initial='HERE', choices=LEAVING_CHOICES)

    def default_title(self):
        return 'Appointment'

    def to_career_event(self, form):
        event = super(AppointmentEventType, self).__init__(form)
        event.config['spousal_hire'] = form.cleaned_data['spousal_hire']
        event.config['leaving_reason'] = form.cleaned_data['leaving_reason']
        return event


class SalaryBaseEventType(CareerEventType):
    """
    An annual salary update
    """
    affects_salary = True
    class EntryForm(BaseEntryForm):
        step = forms.DecimalField(max_digits=4, decimal_places=2, help_text="Current salary step")
        base_salary = forms.DecimalField(max_digits=8, decimal_places=2, help_text="Base annual salary for this rank + step.")

    def default_title(self):
        return 'Base Salary'

    def to_career_event(self, form):
        event = super(AppointmentEventType, self).__init__(form)
        event.config['step'] = form.cleaned_data['step']
        event.config['base_salary'] = form.cleaned_data['base_salary']
        return event

    def get_salary(self, prev_salary):
        return self.event.base_salary
