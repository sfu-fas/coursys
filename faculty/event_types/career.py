import datetime
import decimal

from django import forms

from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import SalaryAdjust
from faculty.event_types.mixins import TeachingCareerEvent, SalaryCareerEvent


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
    ('HERE', u'\u2014'),  # hasn't left yet
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
    IS_EXCLUSIVE = True
    EVENT_TYPE = 'APPOINT'
    NAME = 'Appointment to Position'
    TO_HTML_TEMPLATE = "{{ event.person.name }}'s event {{ event.title }}"

    class EntryForm(BaseEntryForm):
        CONFIG_FIELDS = ['spousal_hire', 'leaving_reason']
        spousal_hire = forms.BooleanField(initial=False, required=False)
        leaving_reason = forms.ChoiceField(initial='HERE', choices=LEAVING_CHOICES)

    def short_summary(self):
        return "Appointment to position as of %s" % (self.event.start_date)


class SalaryBaseEventHandler(CareerEventHandlerBase, SalaryCareerEvent):
    """
    An annual salary update
    """
    EVENT_TYPE = 'SALARY'
    NAME = "Base Salary Update"
    TO_HTML_TEMPLATE = """{{ event.person.name }}'s event {{ event.title }}"""

    class EntryForm(BaseEntryForm):
        CONFIG_FIELDS = ['step', 'base_salary']
        step = forms.DecimalField(max_digits=4, decimal_places=2, help_text="Current salary step")
        base_salary = forms.DecimalField(max_digits=8, decimal_places=2,
                                         help_text="Base annual salary for this rank + step.")

    @property
    def default_title(self):
        return 'Base Salary %s' % (datetime.date.today().year)

    def short_summary(self):
        return "Base salary of %s at step %s" % (self.event.config.get('base_salary', 0),
                                                 self.event.config.get('step', 0))

    def salary_adjust_annually(self):
        s = decimal.Decimal(self.event.config.get('base_salary', 0))
        return SalaryAdjust(s, 1, 0)


class TenureApplicationEventHandler(CareerEventHandlerBase):
    """
    Tenure Application Career event
    """
    EVENT_TYPE = 'TENUREAPP'
    NAME = "Tenure Application"
    IS_INSTANT = True
    TO_HTML_TEMPLATE = """{{ event.person.name }}'s event {{ event.title }}"""

    @property
    def default_title(self):
        return 'Applied for Tenure'

    def short_summary(self):
        return '%s Applied for Tenure on %s' % (self.event.person.name(),
                                                datetime.date.today())

class TenureReceivedEventHandler(CareerEventHandlerBase):
    """
    Received Tenure Career event
    """
    EVENT_TYPE = 'TENUREREC'
    NAME = "Tenure Received"
    IS_INSTANT = True
    TO_HTML_TEMPLATE = """{{ event.person.name }}'s event {{ event.title }}"""

    @property
    def default_title(self):
        return 'Tenure Received'

    def short_summary(self):
        return '%s received for Tenure on %s' % (self.event.person.name(),
                                                datetime.date.today())
