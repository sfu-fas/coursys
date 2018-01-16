import fractions
import itertools

from django import forms
from django.utils.safestring import mark_safe
from django.http import HttpResponse

from faculty.event_types import fields, search
from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.choices import Choices
from faculty.event_types.base import SalaryAdjust, TeachingAdjust
from faculty.event_types.mixins import TeachingCareerEvent, SalaryCareerEvent
from faculty.event_types.constants import SALARY_STEPS_CHOICES
from dashboard.letters import yellow_form_limited, yellow_form_tenure

RANK_CHOICES = Choices(
    ('LLEC', 'Limited-Term Lecturer'),
    ('LABI', 'Laboratory Instructor'),
    ('LECT', 'Lecturer'),
    ('SLEC', 'Senior Lecturer'),
    ('INST', 'Instructor'),
    ('ASSI', 'Assistant Professor'),
    ('ASSO', 'Associate Professor'),
    ('FULL', 'Full Professor'),
    ('URAS', 'University Research Associate'),
    ('ADJC', 'Adjunct Professor'),
    #('UNIV', 'University Professor'),
    #('UNIR', 'University Research Professor'),
)

CONTRACT_REVIEW_CHOICES = Choices(
    ('PEND', 'Pending'),
    ('PROM', 'Renewed'),
    ('DENY', 'Denied'),
)


class AppointmentEventHandler(CareerEventHandlerBase):
    """
    The big career event: from hiring to leaving the position.
    """

    EVENT_TYPE = 'APPOINT'
    NAME = 'Appointment to Position'

    IS_EXCLUSIVE = True

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Position Number</dt><dd>{{ handler|get_display:"position_number" }}</dd>
        <dt>Leaving Reason</dt><dd>{{ handler|get_display:"leaving_reason" }}</dd>
        <dt>Spousal Hire</dt><dd>{{ handler|get_display:"spousal_hire"|yesno }}</dd>

        {% if handler|get_config:"degree1" != 'unknown' and  handler|get_config:"degree1" != ''%}
        <dt>Degrees Held</dt>
        <dd>{{ handler|get_display:"degree1" }}, {{ handler|get_display:"year1" }},
        {{ handler|get_display:"institution1" }}, {{ handler|get_display:"location1" }}
        {% if handler|get_config:"degree2" != 'unknown' and handler|get_config:"degree2" != ''%}<br>
        <dd>{{ handler|get_display:"degree2" }}, {{ handler|get_display:"year2" }},
        {{ handler|get_display:"institution2" }}, {{ handler|get_display:"location2" }}{% endif %}
        {% if handler|get_config:"degree3" != 'unknown' and handler|get_config:"degree3" != '' %}<br>
        <dd>{{ handler|get_display:"degree3" }},  {{ handler|get_display:"year3" }},
        {{ handler|get_display:"institution3" }}, {{ handler|get_display:"location3" }}{% endif %}
        {% endif %}
        {% if handler|get_config:"teaching_semester_credits" != 'unknown' and  handler|get_config:"teaching_semester_credits" != ''%}
        <dt>Teaching Semester Credits</dt><dd>{{ handler|get_config:"teaching_semester_credits" }}</dd>
        {% endif %}

        {% endblock %}
    """

    PDFS = {'yellow1': 'Yellow Form for Tenure Track',
            'yellow2': 'Yellow Form for Limited Term'}

    class EntryForm(BaseEntryForm):

        LEAVING_CHOICES = Choices(
            ('HERE', '\u2014'),  # hasn't left yet
            ('RETI', 'Retired'),
            ('END', 'Limited-term contract ended'),
            ('UNIV', 'Left: job at another University'),
            ('PRIV', 'Left: private-sector job'),
            ('GONE', 'Left: employment status unknown'),
            ('FIRE', 'Dismissal'),
            ('DIED', 'Deceased'),
            ('OTHR', 'Other/Unknown'),
        )

        position_number = forms.CharField(initial='', required=False, widget=forms.TextInput(attrs={'size': '6'}))
        spousal_hire = forms.BooleanField(initial=False, required=False)
        leaving_reason = forms.ChoiceField(initial='HERE', choices=LEAVING_CHOICES)
        degree1 = forms.CharField(max_length=12, help_text='These are the degrees to be inserted into the '
                                                           'Recommendation for Appointment Forms (AKA "Yellow Form"). '
                                                           ' List the highest degree first.', required=False,
                                  label='Degree 1', widget=forms.TextInput(attrs={'size': '13'}))
        year1 = forms.CharField(max_length=5, required=False, label='Year 1', widget=forms.TextInput(attrs={'size': '5'}))
        institution1 = forms.CharField(max_length=25, required=False, label='Institution 1')
        location1 = forms.CharField(max_length=23, required=False, label='City/Country 1')
        degree2 = forms.CharField(max_length=12, required=False, label='Degree 2',
                                  widget=forms.TextInput(attrs={'size': '13'}))
        year2 = forms.CharField(max_length=5, required=False, label='Year 2', widget=forms.TextInput(attrs={'size': '5'}))
        institution2 = forms.CharField(max_length=25, required=False, label='Institution 2')
        location2 = forms.CharField(max_length=23, required=False, label='City/Country 2')
        degree3 = forms.CharField(max_length=12, required=False, label='Degree 3',
                                  widget=forms.TextInput(attrs={'size': '13'}))
        year3 = forms.CharField(max_length=5, required=False, label='Year 3', widget=forms.TextInput(attrs={'size': '5'}))
        institution3 = forms.CharField(max_length=25, required=False, label='Institution 3')
        location3 = forms.CharField(max_length=23, required=False, label='City/Country 3')
        teaching_semester_credits = forms.DecimalField(max_digits=3, decimal_places=0, required=False,
                                                       help_text='Number of teaching semester credits, for the tenure '
                                                       'track form')


    SEARCH_RULES = {
        'position_number': search.StringSearchRule,
        'spousal_hire': search.BooleanSearchRule,
        'leaving_reason': search.ChoiceSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'position_number',
        'spousal_hire',
        'leaving_reason',
    ]

    def get_leaving_reason_display(self):
        return self.EntryForm.LEAVING_CHOICES.get(self.get_config('leaving_reason'), 'N/A')

    def short_summary(self):
        return "Appointment to position"

    def generate_pdf(self, key):
        response = HttpResponse(content_type="application/pdf")
        response['Content-Disposition'] = 'inline; filename="yellowform.pdf"'
        if key == 'yellow1':
            yellow_form_tenure(self, response)
            return response
        if key == 'yellow2':
            yellow_form_limited(self, response)
            return response





class SalaryBaseEventHandler(CareerEventHandlerBase, SalaryCareerEvent):
    """
    An annual salary update
    """

    EVENT_TYPE = 'SALARY'
    NAME = "Base Salary Update"

    IS_EXCLUSIVE = True

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% load humanize %}{% block dl %}
        <dt>Rank &amp; Step</dt><dd>{{ handler|get_display:"rank" }}, step {{ handler|get_display:"step" }}</dd>
        <dt>Base salary</dt><dd>${{ handler|get_display:"base_salary"|floatformat:2|intcomma}}</dd>
        <dt>Add salary</dt><dd>${{ handler|get_display:"add_salary"|floatformat:2|intcomma }}</dd>
        <dt>Add pay</dt><dd>${{ handler|get_display:"add_pay"|floatformat:2|intcomma }}</dd>
        <dt>Total</dt><dd>${{ total|floatformat:2|intcomma }}</dd>
        <!--<dt>Biweekly</dt><dd>${{ biweekly|floatformat:2 }}</dd>-->
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):
        rank = forms.ChoiceField(choices=RANK_CHOICES, required=True)
        step = forms.DecimalField(max_digits=4, decimal_places=2,
                                  help_text="Current salary step")
        base_salary = fields.AddSalaryField(help_text="Base annual salary for this rank + step.")
        add_salary = fields.AddSalaryField()
        add_pay = fields.AddPayField()

        def post_init(self):
            # find the last-known rank as a default
            if self.person:
                from faculty.models import CareerEvent
                event = CareerEvent.objects.filter(person=self.person, event_type='SALARY').effective_now().last()
                if event:
                    self.fields['rank'].initial = event.config['rank']


    SEARCH_RULES = {
        'rank': search.ChoiceSearchRule,
        'base_salary': search.ComparableSearchRule,
        'step': search.ComparableSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'rank',
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

    def get_rank_display(self):
        return RANK_CHOICES.get(self.get_config('rank'), 'Unknown Rank')

    @classmethod
    def default_title(cls):
        return 'Base Salary'

    def short_summary(self):
        return "{2} step {1} at ${0}".format(self.get_config('base_salary'),
                                                     self.get_config('step'), self.get_rank_display())

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
            ('RETENTION', 'Retention Award'),
            ('MARKETDIFF', 'Market Differential'),
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
        return "{0}: ${1}".format(self.get_source_display(),
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
    IS_INSTANT = False

    TO_HTML_TEMPLATE = '''{% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Result</dt><dd>{{ handler|get_display:"result" }}</dd>
        {% endblock %}'''

    class EntryForm(BaseEntryForm):
        RESULT_CHOICES = Choices(
            ('PEND', 'Pending'),
            ('RECI', 'Tenured'),
            ('DENI', 'Denied'),
        )

        result = forms.ChoiceField(label='Result', choices=RESULT_CHOICES,
                                   help_text='The end date of this event is assumed to be when this decision is effective.')


    SEARCH_RULES = {
        'result': search.ChoiceSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'result',
    ]

    def get_result_display(self):
        return self.EntryForm.RESULT_CHOICES.get(self.get_config('result'), 'unknown outcome')

    def short_summary(self):
        return "Tenure application: {0}".format(self.get_result_display(),)


class PromotionApplicationEventHandler(CareerEventHandlerBase):
    """
    Promotion Application Career event
    """
    EVENT_TYPE = 'PROMOTION'
    NAME = "Promotion Application"
    IS_INSTANT = False

    TO_HTML_TEMPLATE = '''{% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Rank applied for</dt><dd>{{ handler|get_display:"rank" }}</dd>
        <dt>Result</dt><dd>{{ handler|get_display:"result" }}</dd>
        <dt>Steps Year One</dt><dd>{{ handler|get_display:"steps" }} <span class="helptext">(step increase in the first year after promotion)</span></dd>
        <dt>Steps Year Two</dt><dd>{{ handler|get_display:"steps2" }} <span class="helptext">(step increase in the second year after promotion)</span></dd>
        {% endblock %}'''

    class EntryForm(BaseEntryForm):
        RESULT_CHOICES = Choices(
            ('PEND', 'Pending'),
            ('RECI', 'Promoted'),
            ('DENI', 'Denied'),
        )

        rank = forms.ChoiceField(choices=RANK_CHOICES, required=True, 
                help_text='Rank being applied for (promoted to if successful)')
        result = forms.ChoiceField(label='Result', choices=RESULT_CHOICES,
                help_text='The end date of this event is assumed to be when this decision is effective.')
        steps = forms.ChoiceField(label='Steps Year One', choices=SALARY_STEPS_CHOICES,
                help_text=mark_safe('Annual step increase given for the <strong>first</strong> year after promotion'))
        steps2 = forms.ChoiceField(label='Steps Year Two', choices=SALARY_STEPS_CHOICES,
                help_text=mark_safe('Annual step increase given for the <strong>second</strong> year after promotion'))


    SEARCH_RULES = {
        'result': search.ChoiceSearchRule,
        'steps': search.ComparableSearchRule,
        'steps2': search.ComparableSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'result',
        'steps',
        'steps2',
    ]
    SEARCH_FIELD_NAMES = {
        'steps': 'Steps Year One',
        'steps2': 'Steps Year Two',
    }

    def get_rank_display(self):
        return RANK_CHOICES.get(self.get_config('rank'), 'unknown rank')
    def get_result_display(self):
        return self.EntryForm.RESULT_CHOICES.get(self.get_config('result'), 'unknown outcome')
    def get_steps_display(self):
        return SALARY_STEPS_CHOICES.get(self.get_config('steps'), 'unknown outcome')
    def get_steps2_display(self):
        return SALARY_STEPS_CHOICES.get(self.get_config('steps2'), 'unknown outcome')

    def short_summary(self):
        return "Promotion application: {0}".format(self.get_result_display(),)


class SalaryReviewEventHandler(CareerEventHandlerBase):
    EVENT_TYPE = 'SALARYREV'
    NAME = "Salary Review"
    IS_INSTANT = False

    TO_HTML_TEMPLATE = '''{% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Steps Granted</dt><dd>{{ handler|get_display:"steps" }}</dd>
        {% endblock %}'''

    class EntryForm(BaseEntryForm):

        steps = forms.ChoiceField(label='Steps', choices=SALARY_STEPS_CHOICES,
                                   help_text='Annual step increase given')


    SEARCH_RULES = {
        'steps': search.ComparableSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'steps',
    ]

    def get_steps_display(self):
        return SALARY_STEPS_CHOICES.get(self.get_config('steps'), 'unknown outcome')
    def short_summary(self):
        return "Salary Review: {0}".format(self.get_steps_display(),)

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
            ('LOA', 'Leave of Absence'),
            ('SECONDMENT', 'Secondment'),
        )
        reason = forms.ChoiceField(label='Type', choices=REASONS)
        leave_fraction = fields.FractionField(help_text="Fraction of salary received during leave eg. '3/4' indicates 75% pay",
                                              label='Work fraction', initial=1)
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
        try:
            frac = fractions.Fraction(self.get_config('leave_fraction'))
        except TypeError:
            frac = 0

        return '%s Leave @ %.0f%%' % (self.get_reason_display(), frac*100)

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
        <dt>Option</dt><dd>{{ handler|get_display:"option" }} </dd>
        <dt>Pay Fraction</dt><dd>{{ handler|get_display:"pay_fraction" }}</dd>
        <dt>Report Received</dt><dd>{{ handler|get_display:"report_received"|yesno }}</dd>
        <dt>Report Received On</dt><dd>{{ handler|get_display:"report_received_date" }}</dd>
        <dt>Teaching Load Decrease</dt><dd>{{ handler|get_display:"teaching_decrease" }}</dd>
        <dt>Deferred Salary</dt><dd>{{ handler|get_display:"deferred_salary"|yesno }}</dd>
        <dt>Accumulated Credits</dt><dd>{{ handler|get_display:"accumulated_credits" }}</dd>
        <dt>Study Leave Credits Spent</dt><dd>{{ handler|get_display:"study_leave_credits" }}</dd>
        <dt>Study Leave Credits Carried Forward</dt><dd>{{ handler|get_display:"credits_forward" }}</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):
        PAY_FRACTION_CHOICES = [
            ('4/5', '80%'),
            ('9/10', '90%'),
            ('1', '100%'),
        ]
        option = forms.CharField(min_length=1, max_length=1, required=False,
                                 help_text='The option for this study leave.  A, B, C, etc',
                                 widget=forms.TextInput(attrs={'size': '1'}))
        pay_fraction = fields.FractionField(choices=PAY_FRACTION_CHOICES)
        report_received = forms.BooleanField(label='Report Received?', initial=False, required=False)
        report_received_date = fields.SemesterField(required=False, semester_start=False)
        teaching_decrease = fields.TeachingReductionField()
        deferred_salary = forms.BooleanField(label='Deferred Salary?', initial=False, required=False)
        accumulated_credits = forms.IntegerField(label='Accumulated Credits', min_value=0, max_value=99,
                                                 help_text='Accumulated unused credits', required=False)
        study_leave_credits = forms.IntegerField(label='Study Leave Credits Spent', min_value=0, max_value=99,
                                                 help_text='Total number of Study Leave Credits spent for entire leave')
        credits_forward = forms.IntegerField(label='Study Leave Credits Carried Forward', required=False, min_value=0,
                                             max_value=10000,
                                             help_text='Study Credits Carried Forward After Leave (may be left blank if unknown)')

        def post_init(self):
            # finding the teaching load and set the decrease to that value
            if (self.person):
                from faculty.util import ReportingSemester
                from faculty.processing import FacultySummary
                semester = ReportingSemester(self.initial['start_date'])
                teaching_load = abs(FacultySummary(self.person).teaching_credits(semester)[1])
            else:
                teaching_load = 0

            self.fields['teaching_decrease'].initial = teaching_load

    SEARCH_RULES = {
        'pay_fraction': search.ComparableSearchRule,
        'report_received': search.BooleanSearchRule,
        'teaching_decrease': search.ComparableSearchRule,
        'study_leave_credits': search.ComparableSearchRule,
        'credits_forward': search.ComparableSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'pay_fraction',
        'report_received',
        'report_received_date',
        'teaching_decrease',
        'study_leave_credits',
        'credits_forward'
    ]

    from django.conf.urls import url

    EXTRA_LINKS = {'Teaching Summary': 'faculty:teaching_summary'}

    @classmethod
    def default_title(cls):
        return 'Study Leave'

    def get_pay_fraction_display(self):
        try:
            frac = fractions.Fraction(self.get_config('pay_fraction'))
        except TypeError:
            frac = 0
        return '%.0f%%' % (frac*100)

    def short_summary(self):
        return 'Study Leave @ ' + self.get_pay_fraction_display()

    def salary_adjust_annually(self):
        pay_fraction = self.get_config('pay_fraction')
        return SalaryAdjust(0, pay_fraction, 0)

    def teaching_adjust_per_semester(self):
        credits = self.get_config('teaching_decrease')
        return TeachingAdjust(fractions.Fraction(0), credits)

    def get_credits_carried_forward(self):
        return self.get_config('credits_forward')

    def get_study_leave_credits(self):
        return self.get_config('study_leave_credits')


class AccreditationFlagSearchRule(search.ChoiceSearchRule):
    """A hack to make viewer specific choice fields work."""

    def make_value_field(self, viewer, member_units):
        field = super(AccreditationFlagSearchRule, self).make_value_field(viewer, member_units)

        from faculty.models import EventConfig
        ecs = EventConfig.objects.filter(unit__in=member_units,
                                         event_type=AccreditationFlagEventHandler.EVENT_TYPE)
        field.choices += itertools.chain(*[ec.config.get('flags', []) for ec in ecs])

        return field


class AccreditationFlagEventHandler(CareerEventHandlerBase):
    """
    Aquisition of a accreditation-related property
    """

    EVENT_TYPE = 'ACCRED'
    NAME = 'Accreditation Attribute'

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Attribute</dt><dd>{{ handler|get_display:"flag" }}</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):
        flag = forms.ChoiceField(required=True, choices=[], label='Attribute')

        def post_init(self):
            # set the allowed position choices from the config from allowed units
            from faculty.models import EventConfig
            ecs = EventConfig.objects.filter(unit__in=self.units,
                                             event_type=AccreditationFlagEventHandler.EVENT_TYPE)
            choices = itertools.chain(*[ec.config.get('flags', []) for ec in ecs])
            self.fields['flag'].choices = choices

        def clean(self):
            from faculty.models import EventConfig
            data = self.cleaned_data
            if 'unit' not in data:
                raise forms.ValidationError("Couldn't check unit for attribute ownership.")

            found = False
            try:
                ec = EventConfig.objects.get(unit=data['unit'],
                                             event_type=AccreditationFlagEventHandler.EVENT_TYPE)
                flags = dict(ec.config.get('flags', []))
                if data['flag'] in flags:
                    found = True
            except EventConfig.DoesNotExist:
                pass

            if not found:
                raise forms.ValidationError("That attribute is not owned by the selected unit.")

            return data

    SEARCH_RULES = {
        'flag': AccreditationFlagSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'flag',
    ]

    def get_flag_display(self):
        """
        Get the name of this flag, for display to the user
        """
        from faculty.models import EventConfig
        try:
            ec = EventConfig.objects.get(unit=self.event.unit, event_type=self.EVENT_TYPE)
            fellowships = dict(ec.config.get('flags', {}))
        except EventConfig.DoesNotExist:
            fellowships = {}

        flag = self.event.config.get('flag', '???')
        return fellowships.get(flag, flag)

    @classmethod
    def default_title(cls):
        return 'Accreditation Flag'

    def short_summary(self):
        return "Has {0}".format(self.get_flag_display())

class ContractReviewEventHandler(CareerEventHandlerBase):
    EVENT_TYPE = 'CONTRACTRV'
    NAME = "Contract Renewal"
    IS_INSTANT = False

    TO_HTML_TEMPLATE = '''
        {% extends "faculty/event_base.html" %}
            {% load event_display %}
            {% block dl %}
            <dt>Result</dt>
            <dd>{{ handler|get_display:"result" }}</dd>
        {% endblock %}'''

    class EntryForm(BaseEntryForm):
        result = forms.ChoiceField(label='Result', choices=CONTRACT_REVIEW_CHOICES)

    SEARCH_RULES = {
        'result': search.ComparableSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'result',
    ]

    def get_result_display(self):
        return CONTRACT_REVIEW_CHOICES.get(self.get_config('result'), 'unknown outcome')
    def short_summary(self):
        return "Contract Renewal: {0}".format(self.get_result_display(),)
