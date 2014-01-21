# career-level event types: appointment, salary

from base import CareerEventHandlerBase, BaseEntryForm
from django import forms
import decimal, datetime

RANK_CHOICES = [
        ('LABI', 'Laboratory Instructor'),
        ('LECT', 'Lecturer'),
        ('SLEC', 'Senior Lecturer'),
        ('INST', 'Instructor'),
        ('ASSI', 'Assistant Professor'),
        ('ASSO', 'Associate Professor'),
        ('FULL', 'Full Professor'),
        #('UNIV', 'University Professor'),
        #('UNIR', 'University Research Professor'),
        ]

LEAVING_CHOICES = [
        ('HERE', u'\u2014'), # hasn't left yet
        ('RETI', 'Retired'),
        ('END', 'Limited-term contract ended'),
        ('UNIV', 'Left: job at another University'),
        ('PRIV', 'Left: private-sector job'),
        ('GONE', 'Left: employment status unknown'),
        ('FIRE', 'Dismissal'),
        ('DIED', 'Deceased'),
        ('OTHR', 'Other/Unknown'),
        ]


class AppointmentEventHandler(CareerEventHandlerBase):
    """
    The big career event: from hiring to leaving the position.
    """
    TO_HTML_TEMPLATE = """{{ faculty.name }}: {{ event.title }}"""

    class EntryForm(BaseEntryForm):
        spousal_hire = forms.BooleanField(initial=False)
        leaving_reason = forms.ChoiceField(initial='HERE', choices=LEAVING_CHOICES)

    @property
    def default_title(self):
        return 'Appointment'

    def to_career_event(self, form):
        event = super(AppointmentEventHandler, self).to_career_event(form)
        event.config['spousal_hire'] = form.cleaned_data['spousal_hire']
        event.config['leaving_reason'] = form.cleaned_data['leaving_reason']
        return event


class SalaryBaseEventHandler(CareerEventHandlerBase):
    """
    An annual salary update
    """
    TO_HTML_TEMPLATE = """{{ faculty.name }}: {{ event.title }}"""

    affects_salary = True
    class EntryForm(BaseEntryForm):
        step = forms.DecimalField(max_digits=4, decimal_places=2, help_text="Current salary step")
        base_salary = forms.DecimalField(max_digits=8, decimal_places=2, help_text="Base annual salary for this rank + step.")

    @property
    def default_title(self):
        return 'Base Salary %s' % (datetime.date.today().year)

    def to_career_event(self, form):
        event = super(SalaryBaseEventHandler, self).to_career_event(form)
        event.config['step'] = form.cleaned_data['step']
        event.config['base_salary'] = form.cleaned_data['base_salary']
        return event

    def get_salary(self, prev_salary):
        return decimal.Decimal(10000)
        #return self.event.base_salary
