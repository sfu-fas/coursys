import fractions

from django import forms

from faculty.event_types import fields, search
from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import Choices
from faculty.event_types.base import SalaryAdjust, TeachingAdjust
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


class AppointmentEventHandler(CareerEventHandlerBase):
    """
    The big career event: from hiring to leaving the position.
    """

    EVENT_TYPE = 'APPOINT'
    NAME = 'Appointment to Position'

    IS_EXCLUSIVE = True
    #VIEWABLE_BY = 'FAC'

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Leaving Reason</dt><dd>{{ handler|get_display:"leaving_reason" }}</dd>
        <dt>Spousal hire</dt><dd>{{ handler|get_display:"spousal_hire"|yesno }}</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):

        LEAVING_CHOICES = Choices(
            ('HERE', u'\u2014'),  # hasn't left yet
            ('RETI', 'Retired'),
            ('END', 'Limited-term contract ended'),
            ('UNIV', 'Left: job at another University'),
            ('PRIV', 'Left: private-sector job'),
            ('GONE', 'Left: employment status unknown'),
            ('FIRE', 'Dismissal'),
            ('DIED', 'Deceased'),
            ('OTHR', 'Other/Unknown'),
        )

        spousal_hire = forms.BooleanField(initial=False, required=False)
        leaving_reason = forms.ChoiceField(initial='HERE', choices=LEAVING_CHOICES)

    SEARCH_RULES = {
        'spousal_hire': search.BooleanSearchRule,
        'leaving_reason': search.ChoiceSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'spousal_hire',
        'leaving_reason',
    ]

    def get_leaving_reason_display(self):
        return self.EntryForm.LEAVING_CHOICES.get(self.get_config('leaving_reason'), 'N/A')

    def short_summary(self):
        return "Appointment to position as of %s" % (self.event.start_date)


class SalaryBaseEventHandler(CareerEventHandlerBase, SalaryCareerEvent):
    """
    An annual salary update
    """

    EVENT_TYPE = 'SALARY'
    NAME = "Base Salary Update"

    IS_EXCLUSIVE = True

    APPROVAL_BY = 'DEPT'

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Base salary</dt><dd>${{ handler|get_display:"base_salary"|floatformat:2 }}</dd>
        <dt>Add salary</dt><dd>${{ handler|get_display:"add_salary"|floatformat:2 }}</dd>
        <dt>Add pay</dt><dd>${{ handler|get_display:"add_pay"|floatformat:2 }}</dd>
        <dt>Total</dt><dd>${{ total|floatformat:2 }}</dd>
        <!--<dt>Biweekly</dt><dd>${{ biweekly|floatformat:2 }}</dd>-->
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):
        step = forms.DecimalField(max_digits=4, decimal_places=2,
                                  help_text="Current salary step")
        base_salary = fields.AddSalaryField(help_text="Base annual salary for this rank + step.")
        add_salary = fields.AddSalaryField()
        add_pay = fields.AddPayField()

    SEARCH_RULES = {
        'base_salary': search.ComparableSearchRule,
        'step': search.ComparableSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'base_salary',
        'step',
    ]

    def to_html_context(self):
        total = self.get_config('base_salary')
        total += self.get_config('add_salary')
        total += self.get_config('add_pay')
        return {
            'total': total,
            'biweekly': total/365*14,
        }

    @classmethod
    def default_title(cls):
        return 'Base Salary'

    def short_summary(self):
        return "Base salary of %s at step %s".format(self.get_config('base_salary'),
                                                     self.get_config('step'))

    def salary_adjust_annually(self):
        salary = self.get_config('base_salary')
        add_salary = self.get_config('add_salary')
        add_pay = self.get_config('add_pay')
        return SalaryAdjust(salary + add_salary, 1, add_pay)


class SalaryModificationEventHandler(CareerEventHandlerBase, SalaryCareerEvent):
    """
    Salary modification/stipend event
    """

    EVENT_TYPE = 'STIPEND'
    NAME = "Salary Modification/Stipend"

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Source</dt><dd>{{ handler|get_display:"source" }}</dd>
        <dt>Amount</dt><dd>${{ handler|get_display:"amount" }}</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):

        STIPEND_SOURCES = Choices(
            ('RETENTION', 'Retention/Market Differential'),
            ('RESEARCH', 'Research Chair Stipend'),
            ('OTHER', 'Other'),
        )

        source = forms.ChoiceField(label='Stipend Source', choices=STIPEND_SOURCES)
        # Do we want this to be adjusted during leaves?
        amount = fields.AddSalaryField()

    SEARCH_RULES = {
        'source': search.ChoiceSearchRule,
        'amount': search.ComparableSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'source',
        'amount',
    ]

    def get_source_display(self):
        return self.EntryForm.STIPEND_SOURCES.get(self.get_config('source'), 'N/A')

    @classmethod
    def default_title(cls):
        return 'Salary Modification / Stipend'

    def short_summary(self):
        return "%s for $%s".format(self.get_config('source'),
                                   self.get_config('amount'))

    def salary_adjust_annually(self):
        amount = self.get_config('amount')
        return SalaryAdjust(amount, 1, 0)


class TenureApplicationEventHandler(CareerEventHandlerBase):
    """
    Tenure Application Career event
    """

    EVENT_TYPE = 'TENUREAPP'
    NAME = "Tenure Application"

    IS_INSTANT = True

    TO_HTML_TEMPLATE = '{% extends "faculty/event_base.html" %}'

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

    TO_HTML_TEMPLATE = '{% extends "faculty/event_base.html" %}'

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

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Leave Type</dt><dd>{{ handler|get_display:"reason" }}</dd>
        <dt>Leave Fraction</dt><dd>{{ handler|get_display:"leave_fraction" }}</dd>
        <dt>Teaching Credits</dt><dd>{{ handler|get_display:"teaching_credits" }}</dd>
        <dt>Teaching Load Decrease</dt><dd>{{ handler|get_display:"teaching_load_decrease" }}</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):
        REASONS = Choices(
            ('MEDICAL', 'Medical'),
            ('PARENTAL', 'Parental'),
            ('ADMIN', 'Admin'),
            ('SECONDMENT', 'Secondment'),
        )
        reason = forms.ChoiceField(label='Type', choices=REASONS)
        leave_fraction = fields.FractionField(help_text="Fraction of salary received during leave eg. '3/4' indicates 75% pay", label='Work fraction')
        teaching_credits = fields.TeachingCreditField()
        teaching_load_decrease = fields.TeachingReductionField()

    SEARCH_RULES = {
        'reason': search.ChoiceSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'reason',
    ]

    def get_reason_display(self):
        return self.EntryForm.REASONS.get(self.get_config('reason'), 'N/A')

    @classmethod
    def default_title(cls):
        return 'On Leave'

    def short_summary(self):
        return '%s leave beginning %s'.format(self.event.person.name(),
                                              self.event.start_date)

    def salary_adjust_annually(self):
        leave_fraction = self.get_config('leave_fraction')
        return SalaryAdjust(0, leave_fraction, 0)

    def teaching_adjust_per_semester(self):
        credits = self.get_config('teaching_credits')
        load_decrease = self.get_config('teaching_load_decrease')
        return TeachingAdjust(credits, load_decrease)


class StudyLeaveEventHandler(CareerEventHandlerBase, SalaryCareerEvent, TeachingCareerEvent):
    """
    Study leave event
    """

    EVENT_TYPE = 'STUDYLEAVE'
    NAME = "Study Leave"

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Pay Fraction</dt><dd>{{ handler|get_display:"pay_fraction" }}</dd>
        <dt>Report Received</dt><dd>{{ handler|get_display:"report_received"|yesno }}</dd>
        <dt>Report Received On</dt><dd>{{ handler|get_display:"report_received_date" }}</dd>
        <dt>Credits Carried Forward</dt><dd>{{ handler|get_display:"credits" }}</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):
        pay_fraction = fields.FractionField(help_text="eg. 2/3")
        report_received = forms.BooleanField(label='Report Received?', initial=False, required=False)
        report_received_date = fields.SemesterField(required=False, semester_start=False)
        credits = fields.TeachingCreditField()

    SEARCH_RULES = {
        'pay_fraction': search.ComparableSearchRule,
        'report_received': search.BooleanSearchRule,
        'credits': search.ComparableSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'pay_fraction',
        'report_received',
        'report_received_date',
        'credits',
    ]

    @classmethod
    def default_title(cls):
        return 'Study Leave'

    def short_summary(self):
        return 'Study leave begginging %s'.format(self.event.start_date)

    def salary_adjust_annually(self):
        pay_fraction = self.get_config('pay_fraction')
        return SalaryAdjust(0, pay_fraction, 0)

    def teaching_adjust_per_semester(self):
        credits = self.get_config('credits')
        return TeachingAdjust(credits, fractions.Fraction(0))
