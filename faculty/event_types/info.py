from django import forms

from coredata.models import Unit

from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import Choices


class ExternalAffiliationHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'EXTERN_AFF'
    NAME = 'External Affiliation'

    TO_HTML_TEMPLATE = '''
{% extends 'faculty/event_base.html' %}
{% load event_display %}
{% block dl %}
<dt>Organization Name</dt><dd>{{ handler|get_config:'org_name' }}</dd>
<dt>Organization Type</dt><dd>{{ handler.get_org_type_display }}</dd>
<dt>Organization Class</dt><dd>{{ handler.get_org_class_display }}</dd>
<dt>Is Research Institute / Centre?</dt><dd>{{ handler|get_config:'is_research' }}</dd>
<dt>Is Adjunct?</dt><dd>{{ handler|get_config:'is_adjunct' }}</dd>
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

    @classmethod
    def default_title(cls):
        return 'Affiliated with '

    def get_org_type_display(self):
        return self.EntryForm.ORG_TYPES[self.get_config('org_type')]

    def get_org_class_display(self):
        return self.EntryForm.ORG_CLASSES[self.get_config('org_class')]

    def short_summary(self):
        # TODO: Figure out a nicer format that includes all relevant information.
        org_name = self.get_config('org_name')
        org_type = self.get_org_type_display()
        org_class = self.get_org_class_display()
        return 'Affiliated with {} - a {} {}'.format(org_name, org_type, org_class)


class CommitteeMemberHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'COMMITTEE'
    NAME = 'Committee Member'

    TO_HTML_TEMPLATE = '''
{% extends 'faculty/event_base.html' %}
{% load event_display %}
{% block dl %}
<dt>Committee Name</dt><dd>{{ handler|get_config:'committee_name' }}</dd>
<dt>Committee Unit</dt><dd>{{ handler|get_config:'committee_unit' }}</dd>
{% endblock %}
'''

    class EntryForm(BaseEntryForm):

        committee_name = forms.CharField(label='Committee Name', max_length=255)
        committee_unit = forms.ModelChoiceField(label='Committee Unit',
                                                queryset=Unit.objects.all())

    @classmethod
    def default_title(cls):
        return 'Joined a committee'

    def short_summary(self):
        return 'On the {} committee for the {}'.format(self.get_config('committee_name', ''),
                                                       self.get_config('committee_unit'))
