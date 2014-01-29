# career-level event types: appointment, salary

from base import CareerEventHandlerBase, BaseEntryForm, SalaryAdjust, TeachingAdjust
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
    key = 'APPOINT'
    name = "Appointment to position"
    TO_HTML_TEMPLATE = """{{ faculty.name }}: {{ event.title }}"""

    class EntryForm(BaseEntryForm):
        CONFIG_FIELDS = ['spousal_hire', 'leaving_reason']
        spousal_hire = forms.BooleanField(initial=False, required=False)
        leaving_reason = forms.ChoiceField(initial='HERE', choices=LEAVING_CHOICES)

    @property
    def default_title(self):
        return 'Appointment'


class SalaryBaseEventHandler(CareerEventHandlerBase):
    """
    An annual salary update
    """
    key = 'SALARY'
    name = "Base salary update"
    affects_salary = True
    TO_HTML_TEMPLATE = """{{ faculty.name }}: {{ event.title }}"""

    class EntryForm(BaseEntryForm):
        CONFIG_FIELDS = ['step', 'base_salary']
        step = forms.DecimalField(max_digits=4, decimal_places=2, help_text="Current salary step")
        base_salary = forms.DecimalField(max_digits=8, decimal_places=2, help_text="Base annual salary for this rank + step.")

    @property
    def default_title(self):
        return 'Base Salary %s' % (datetime.date.today().year)

    #def load_form(self, form):
    #    e = super(AppointmentEventHandler, self).load_form(form, config_fields=)
    #    return e

    def salary_adjust_annually(self):
        # s = self.event.base_salary
        s = decimal.Decimal(10000)
        return SalaryAdjust(s, 1, 0)






