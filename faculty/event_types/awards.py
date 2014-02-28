import itertools

from django import forms

from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import SalaryAdjust, TeachingAdjust
from faculty.event_types.base import Choices
from faculty.event_types.fields import DollarInput, AddSalaryField, AddPayField, TeachingCreditField
from faculty.event_types.mixins import TeachingCareerEvent, SalaryCareerEvent
from faculty.event_types.search import ChoiceSearchRule, ComparableSearchRule, StringSearchRule


class FellowshipEventHandler(CareerEventHandlerBase, SalaryCareerEvent, TeachingCareerEvent):
    """
    Appointment to a fellowship/chair
    """

    EVENT_TYPE = 'FELLOW'
    NAME = 'Fellowship / Chair'

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Position</dt><dd>{{ handler|get_display:"position" }}</dd>
        <dt>Add salary</dt><dd>${{ handler|get_display:"add_salary"|floatformat:2 }}</dd>
        <dt>Add pay</dt><dd>${{ handler|get_display:"add_pay"|floatformat:2 }}</dd>
        <dt>Teaching credit</dt><dd>{{ handler|get_display:"teaching_credit" }} (per semester)</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):
        position = forms.ChoiceField(required=True, choices=[])
        add_salary = AddSalaryField(required=False)
        add_pay = AddPayField(required=False)
        teaching_credit = TeachingCreditField(required=False)

        def post_init(self):
            # set the allowed position choices from the config from allowed units
            from faculty.models import EventConfig
            ecs = EventConfig.objects.filter(unit__in=self.units,
                                             event_type=FellowshipEventHandler.EVENT_TYPE)
            choices = itertools.chain(*[ec.config.get('fellowships', []) for ec in ecs])
            self.fields['position'].choices = choices

        def clean(self):
            from faculty.models import EventConfig
            data = self.cleaned_data
            if 'unit' not in data:
                raise forms.ValidationError("Couldn't check unit for fellowship ownership.")

            found = False
            try:
                ec = EventConfig.objects.get(unit=data['unit'],
                                             event_type=FellowshipEventHandler.EVENT_TYPE)
                fellowships = dict(ec.config.get('fellowships', []))
                if data['position'] in fellowships:
                    found = True
            except EventConfig.DoesNotExist:
                pass

            if not found:
                raise forms.ValidationError("That fellowship is not owned by the selected unit.")

            return data

    SEARCH_RULES = {
        'position': StringSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'position',
    ]

    def get_position_display(self):
        """
        Get the name of this fellowship/chair, for display to the user

        """
        from faculty.models import EventConfig
        try:
            ec = EventConfig.objects.get(unit=self.event.unit, event_type=self.EVENT_TYPE)
            fellowships = dict(ec.config.get('fellowships', {}))
        except EventConfig.DoesNotExist:
            fellowships = {}

        pos = self.event.config.get('position', '???')
        return fellowships.get(pos, pos)

    @classmethod
    def default_title(cls):
        return 'Fellowship / Chair'

    def short_summary(self):
        return "Appointment to %s".format(self.get_position_display())

    def salary_adjust_annually(self):
        add_salary = self.get_config('add_salary')
        add_pay = self.get_config('add_pay')
        return SalaryAdjust(add_salary, 1, add_pay)

    def teaching_adjust_per_semester(self):
        adjust = self.get_config('teaching_credit')
        return TeachingAdjust(adjust, adjust)


class TeachingCreditEventHandler(CareerEventHandlerBase, TeachingCareerEvent):
    """
    Received Teaching credit event
    """

    EVENT_TYPE = 'TEACHING'
    NAME = "Teaching Credit Received"

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Teaching Credits</dt><dd>{{ handler|get_display:"teaching_credits" }}</dd>
        <dt>Type</dt><dd>{{ handler|get_display:"category" }}</dd>
        <dt>Reason</dt><dd>{{ handler|get_display:"reason" }}</dd>
        <dt>Approved By</dt><dd>{{ handler|get_display:"approved_by" }}</dd>
        <dt>Funded By</dt><dd>{{ handler|get_display:"funded_by" }}</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):

        CATEGORIES = Choices(
            ('BUYOUT', 'Buyout'),
            ('RELEASE', 'Teaching Release'),
            ('OTHER', 'Other'),
        )

        category = forms.ChoiceField(label='Type', choices=CATEGORIES)
        teaching_credits = TeachingCreditField()
        reason = forms.CharField(max_length=255, required=False)
        funded_by = forms.CharField(label='Funded By', max_length=255, required=False)
        approved_by = forms.CharField(label='Approved By', max_length=255, required=False)

    SEARCH_RULES = {
        'category': ChoiceSearchRule,
        'teaching_credits': ComparableSearchRule,
        'funded_by': StringSearchRule,
        'approved_by': StringSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'category',
        'teaching_credits',
        'funded_by',
        'approved_by',
    ]

    def get_category_display(self):
        return self.EntryForm.CATEGORIES.get(self.get_config('category'), 'N/A')

    @classmethod
    def default_title(cls):
        return 'Recevied Teaching Credit'

    def short_summary(self):
        credit = self.get_config('teaching_credits')
        category = self.get_category_display()
        return 'Received %s teaching credits due to %s'.format(credit, category)

    def teaching_adjust_per_semester(self):
        adjust = self.get_config('teaching_credits')
        return TeachingAdjust(adjust, adjust)


class AwardEventHandler(CareerEventHandlerBase):
    """
    Award Career event
    """

    EVENT_TYPE = 'AWARD'
    NAME = "Award Received"

    IS_INSTANT = True

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Award</dt><dd>{{ handler|get_display:"award"}}</dd>
        <dt>Awarded By</dt><dd>{{ handler|get_display:"awarded_by" }}</dd>
        <dt>Amount</dt><dd>${{ handler|get_display:"amount" }}</dd>
        <dt>Externally Funded?</dt><dd>{{ handler|get_display:"externally_funded"|yesno }}</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):
        award = forms.CharField(label='Award Name', max_length=255)
        awarded_by = forms.CharField(label='Awarded By', max_length=255)
        amount = forms.DecimalField(widget=DollarInput, decimal_places=2, initial=0)
        externally_funded = forms.BooleanField(required=False)

    SEARCH_RULES = {
        'award': StringSearchRule,
        'awarded_by': StringSearchRule,
        'amount': ComparableSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'award',
        'awarded_by',
        'amount',
    ]

    @classmethod
    def default_title(cls):
        return 'Award Received'

    def short_summary(self):
        award = self.get_display('award')
        awarded_by = self.get_display('awarded_by')
        return 'Award: %s reveieved from %s'.format(award, awarded_by)


class GrantApplicationEventHandler(CareerEventHandlerBase):
    """
    Grant Application Career event
    """

    EVENT_TYPE = 'GRANTAPP'
    NAME = "Grant Application"

    IS_INSTANT = True

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Funding Agency</dt><dd>{{ handler|get_display:"funding_agency"}}</dd>
        <dt>Grant Name</dt><dd>{{ handler|get_display:"grant_name" }}</dd>
        <dt>Amount</dt><dd>${{ handler|get_display:"amount" }}</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):
        funding_agency = forms.CharField(label='Funding Agency', max_length=255)
        grant_name = forms.CharField(label='Grant Name', max_length=255)
        amount = forms.DecimalField(widget=DollarInput, decimal_places=2, initial=0)

    SEARCH_RULES = {
        'funding_agency': StringSearchRule,
        'grand_name': StringSearchRule,
        'amount': ComparableSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'funding_agency',
        'grant_name',
        'amount',
    ]

    @classmethod
    def default_title(cls):
        return 'Applied for Grant'

    def short_summary(self):
        funding_agency = self.get_config('funding_agency')
        grant_name = self.get_config('grant_name')
        amount = self.get_config('amount')
        return 'Applied to %s for Grant: %s  for the amount of %s'.format(funding_agency,
                                                                          grant_name,
                                                                          amount)
