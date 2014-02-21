import datetime
import decimal
import fractions

from django import forms

from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import SalaryAdjust, TeachingAdjust
from faculty.event_types.mixins import TeachingCareerEvent, SalaryCareerEvent
from faculty.event_types.fields import AddSalaryField, AddPayField, SemesterField


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
    TO_HTML_TEMPLATE = """{% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Leaving Reason</dt><dd>{{ event|get_config:"leaving_reason" }}</dd>
        <dt>Spousal hire</dt><dd>{{ event|get_config:"spousal_hire"|yesno }}</dd>
        {% endblock %}
        """

    class EntryForm(BaseEntryForm):
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
    IS_EXCLUSIVE = True
    TO_HTML_TEMPLATE = """{% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Base salary</dt><dd>${{ event|get_config:"base_salary"|floatformat:2 }}</dd>
        <dt>Add salary</dt><dd>${{ event|get_config:"add_salary"|floatformat:2 }}</dd>
        <dt>Add pay</dt><dd>${{ event|get_config:"add_pay"|floatformat:2 }}</dd>
        <dt>Total</dt><dd>${{ total|floatformat:2 }}</dd>
        <!--<dt>Biweekly</dt><dd>${{ biweekly|floatformat:2 }}</dd>-->
        {% endblock %}
        """

    class EntryForm(BaseEntryForm):
        step = forms.DecimalField(max_digits=4, decimal_places=2, help_text="Current salary step")
        base_salary = AddSalaryField(help_text="Base annual salary for this rank + step.")
        add_salary = AddSalaryField()
        add_pay = AddPayField()

    @classmethod
    def default_title(cls):
        return 'Base Salary'

    def short_summary(self):
        return "Base salary of %s at step %s" % (self.event.config.get('base_salary', 0),
                                                 self.event.config.get('step', 0))

    def to_html_context(self):
        total = decimal.Decimal(self.event.config.get('base_salary', 0))
        total += decimal.Decimal(self.event.config.get('add_salary', 0))
        total += decimal.Decimal(self.event.config.get('add_pay', 0))
        return {
            'total': total,
            'biweekly': total/365*14,
        }

    def salary_adjust_annually(self):
        s = decimal.Decimal(self.event.config.get('base_salary', 0))
        return SalaryAdjust(s, 1, 0)

class SalaryModificationEventHandler(CareerEventHandlerBase, SalaryCareerEvent):
    """
    Salary modification/stipend event
    """
    EVENT_TYPE = 'STIPEND'
    NAME = "Salary Modification/Stipend"
    TO_HTML_TEMPLATE = """{% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Source</dt><dd>{{ event|get_config:"source" }}</dd>
        <dt>Amount</dt><dd>${{ event|get_config:"amount" }}</dd>
        {% endblock %}
        """

    class EntryForm(BaseEntryForm):
        STIPEND_SOURCES =[('RETENTION', 'Retention/Market Differential'), ('RESEARCH', 'Research Chair Stipend'), ('OTHER', 'Other')]
        source = forms.ChoiceField(label='Stipend Source', choices=STIPEND_SOURCES)
        # Do we want this to be adjusted during leaves?
        amount = AddSalaryField()

    @classmethod
    def default_title(cls):
        return 'Salary Modification/Stipend'

    def short_summary(self):
        return "%s for $%s" % (self.event.config.get('source', 0),
                                            self.event.config.get('amount', 0))

    def salary_adjust_annually(self):
        s = decimal.Decimal(self.event.config.get('amount', 0))
        return SalaryAdjust(s, 1, 0)
        
class TenureApplicationEventHandler(CareerEventHandlerBase):
    """
    Tenure Application Career event
    """
    EVENT_TYPE = 'TENUREAPP'
    NAME = "Tenure Application"
    IS_INSTANT = True
    TO_HTML_TEMPLATE = """{% extends "faculty/event_base.html" %}"""

    @classmethod
    def default_title(cls):
        return 'Applied for Tenure'

    def short_summary(self):
        return '%s Applied for Tenure on %s' % (self.event.person.name(),
                                                self.event.start_date)

class TenureReceivedEventHandler(CareerEventHandlerBase):
    """
    Received Tenure Career event
    """
    EVENT_TYPE = 'TENUREREC'
    NAME = "Tenure Received"
    IS_INSTANT = True
    TO_HTML_TEMPLATE = """{% extends "faculty/event_base.html" %}"""

    @classmethod
    def default_title(cls):
        return 'Tenure Received'

    def short_summary(self):
        return '%s received Tenure on %s' % (self.event.person.name(),
                                                self.event.start_date)

class OnLeaveEventHandler(CareerEventHandlerBase, SalaryCareerEvent, TeachingCareerEvent):
    """
    Taking a sort of leave
    """
    EVENT_TYPE = 'LEAVE'
    NAME = "On Leave"
    TO_HTML_TEMPLATE = """{% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Leave Type</dt><dd>{{ event|get_config:"reason" }}</dd>
        <dt>Leave Fraction</dt><dd>{{ event|get_config:"leave_fraction" }}</dd>
        <dt>Teaching Credits Accrue?</dt><dd>{{ event|get_config:"teaching_accrues"|yesno }}</dd>
        {% endblock %}
        """

    class EntryForm(BaseEntryForm):
        REASONS =[('MEDICAL', 'Medical'), ('PARENTAL', 'Parental'), ('ADMIN', 'Admin'), ('SECONDMENT', 'Secondment')]
        reason = forms.ChoiceField(label='Type', choices=REASONS)
        leave_fraction = forms.DecimalField(decimal_places=2, help_text="eg. 0.7")
        teaching_accrues = forms.BooleanField(label='Do Teaching Credits Accrue During Leave?', initial=False, required=False)


    @classmethod
    def default_title(cls):
        return 'On Leave'

    def short_summary(self):
        return '%s leave beginning %s' % (self.event.person.name(),
                                                self.event.start_date)

    def salary_adjust_annually(self):
        # f = fractions.Fraction(self.event.config.get('leave_fraction', 0))
        f = decimal.Decimal(self.event.config.get('leave_fraction', 0))
        return SalaryAdjust(0, f, 0)

    # Not quite sure how this should be done, do we want a field indicating reduction in workload?
    def teaching_adjust_per_semester(self):
        # if self.event.teaching_accrues:
        #     return TeachingAdjust(Fraction(1), Fraction(0))

        return TeachingAdjust(fractions.Fraction(0), fractions.Fraction(0))

class StudyLeaveEventHandler(CareerEventHandlerBase, SalaryCareerEvent, TeachingCareerEvent):
    """
    Study leave event
    """
    EVENT_TYPE = 'STUDYLEAVE'
    NAME = "Study Leave"
    TO_HTML_TEMPLATE = """{% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Pay Fraction</dt><dd>{{ event|get_config:"pay_fraction" }}</dd>
        <dt>Report Received</dt><dd>{{ event|get_config:"teaching_accrues"|yesno }}</dd>
        <dt>Report Received On</dt><dd>{{ event|get_config:"report_reveived_date" }}</dd>
        <dt>Credits Carried Forward</dt><dd>{{ event|get_config:"credits" }}</dd>
        {% endblock %}
        """

    class EntryForm(BaseEntryForm):
        pay_fraction = forms.DecimalField(decimal_places=2, help_text="eg. 0.7")
        report_received = forms.BooleanField(label='Report Received?', initial=False, required=False)
        report_received_date = SemesterField(required=False, semester_start=False)
        credits = forms.DecimalField(decimal_places=2, help_text="Number of Credits Carried Forward")


    @classmethod
    def default_title(cls):
        return 'Study Leave'

    def short_summary(self):
        return 'Study leave begginging %s' % (self.event.start_date)

    def salary_adjust_annually(self):
        # f = fractions.Fraction(self.event.config.get('pay_fraction', 0))
        f = decimal.Decimal(self.event.config.get('pay_fraction', 0))
        return SalaryAdjust(0, f, 0)

    # Not quite sure how this should be done
    def teaching_adjust_per_semester(self):
        c = fractions.Fraction(self.event.config.get('credits', 0))
        return TeachingAdjust(c, fractions.Fraction(0))