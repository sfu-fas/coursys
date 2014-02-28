import fractions

from django import forms

from coredata.models import Unit

from faculty.event_types import fields, search
from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import Choices
from faculty.event_types.base import SalaryAdjust, TeachingAdjust
from faculty.event_types.mixins import TeachingCareerEvent, SalaryCareerEvent


class ExternalAffiliationHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'EXTERN_AFF'
    NAME = 'External Affiliation'

    TO_HTML_TEMPLATE = '''
        {% extends 'faculty/event_base.html' %}{% load event_display %}{% block dl %}
        <dt>Organization Name</dt><dd>{{ handler|get_display:'org_name' }}</dd>
        <dt>Organization Type</dt><dd>{{ handler|get_display:'org_type'}}</dd>
        <dt>Organization Class</dt><dd>{{ handler|get_display:'org_class'}}</dd>
        <dt>Is Research Institute / Centre?</dt><dd>{{ handler|get_display:'is_research'|yesno }}</dd>
        <dt>Is Adjunct?</dt><dd>{{ handler|get_display:'is_adjunct'|yesno }}</dd>
        {% endblock %}
    '''

    class EntryForm(BaseEntryForm):

        ORG_TYPES = Choices(
            ('SFU', 'Internal SFU'),
            ('ACADEMIC', 'Academic'),
            ('PRIVATE', 'Private Sector'),
        )
        ORG_CLASSES = Choices(
            ('EXTERN_COMP', 'External Company'),
            ('NO_PROFIT', 'Not-For-Profit Institution'),
        )

        org_name = forms.CharField(label='Organization Name', max_length=255)
        org_type = forms.ChoiceField(label='Organization Type', choices=ORG_TYPES)
        org_class = forms.ChoiceField(label='Organization Classification', choices=ORG_CLASSES)
        is_research = forms.BooleanField(label='Research Institute/Centre?', required=False)
        is_adjunct = forms.BooleanField(label='Adjunct?', required=False)

    SEARCH_RULES = {
        'org_name': search.StringSearchRule,
        'org_type': search.ChoiceSearchRule,
        'org_class': search.ChoiceSearchRule,
        'is_adjunct': search.BooleanSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'org_name',
        'org_type',
        'org_class',
        'is_adjunct',
    ]

    def get_org_type_display(self):
        return self.EntryForm.ORG_TYPES.get(self.get_config('org_type'))

    def get_org_class_display(self):
        return self.EntryForm.ORG_CLASSES.get(self.get_config('org_class'))

    @classmethod
    def default_title(cls):
        return 'Affiliated with '

    def short_summary(self):
        org_name = self.get_config('org_name')
        org_type = self.get_org_type_display()
        org_class = self.get_org_class_display()
        return 'Affiliated with {} - a {} {}'.format(org_name, org_type, org_class)


class CommitteeMemberHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'COMMITTEE'
    NAME = 'Committee Member'

    TO_HTML_TEMPLATE = '''
        {% extends 'faculty/event_base.html' %}{% load event_display %}{% block dl %}
        <dt>Committee Name</dt><dd>{{ handler|get_display:'committee_name' }}</dd>
        <dt>Committee Unit</dt><dd>{{ handler|get_display:'committee_unit' }}</dd>
        {% endblock %}
    '''

    class EntryForm(BaseEntryForm):

        committee_name = forms.CharField(label='Committee Name', max_length=255)
        committee_unit = forms.ModelChoiceField(label='Committee Unit',
                                                queryset=Unit.objects.all())

    SEARCH_RULES = {
        'committee_name': search.StringSearchRule,
        'committee_unit': search.ChoiceSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'committee_name',
        'committee_unit',
    ]

    @classmethod
    def default_title(cls):
        return 'Joined a committee'

    def short_summary(self):
        return 'On the {} committee for the {}'.format(self.get_config('committee_name', ''),
                                                       self.get_config('committee_unit'))


class ResearchMembershipHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'LABMEMB'
    NAME = 'Research Group / Lab Membership'

    TO_HTML_TEMPLATE = '''
        {% extends 'faculty/event_base.html' %}{% load event_display %}{% block dl %}
        <dt>Lab Name</dt><dd>{{ handler|get_config:'lab_name' }}</dd>
        <dt>Location</dt><dd>{{ handler|get_config:'location' }}</dd>
        {% endblock %}
        '''

    class EntryForm(BaseEntryForm):

        LOCATION_TYPES = Choices(
            ('SFU', 'Internal SFU'),
            ('ACADEMIC', 'Other Academic'),
            ('EXTERNAL', 'External'),
        )

        lab_name = forms.CharField(label='Research Group / Lab Name', max_length=255)
        location = forms.ChoiceField(choices=LOCATION_TYPES)

    SEARCH_RULES = {
        'lab_name': search.StringSearchRule,
        'location': search.ChoiceSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'lab_name',
        'location',
    ]

    def get_location_display(self):
        return self.EntryForm.LOCATION_TYPES.get(self.get_config('location'), 'N/A')

    @classmethod
    def default_title(cls):
        return 'Member of Reseach Group/Lab'

    def short_summary(self):
        return 'Member of %s'.format(self.get_config('lab_name'))


class ExternalServiceHandler(CareerEventHandlerBase, SalaryCareerEvent, TeachingCareerEvent):
    """
    External Service
    """

    EVENT_TYPE = 'EXTSERVICE'
    NAME = "External Service"

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Add Pay</dt><dd>${{ handler|get_display:"add_pay" }}</dd>
        <dt>Teaching Credits</dt><dd>{{ handler|get_display:"teaching_credits" }}</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):
        add_pay = fields.AddPayField()
        teaching_credits = fields.TeachingCreditField()

    @classmethod
    def default_title(cls):
        return 'External Service'

    def short_summary(self):
        return 'External Service: %s' % (self.event.title)

    def salary_adjust_annually(self):
        add_pay = self.get_config('add_pay')
        return SalaryAdjust(0, 1, add_pay)

    def teaching_adjust_per_semester(self):
        credits = self.get_config('teaching_credits')
        return TeachingAdjust(credits, fractions.Fraction(0))
