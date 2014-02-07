from django import forms

from coredata.models import Unit

from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import Choices


class ExternalAffiliationHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'EXTERN'
    NAME = 'External Affiliation'

    class EntryForm(BaseEntryForm):

        CONFIG_FIELDS = [
            'org_name',
            'org_type',
            'org_class',
            'is_research',
            'is_adjunct',
        ]
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

    @property
    def default_title(self):
        return 'Affiliated with {}'.format(self.event.config.get('org_name', ''))

    def short_summary(self):
        # TODO: Figure out a nicer format that includes all relevant information.
        org_name = self.event.config.get('org_name', '')
        org_type = self.EntryForm.ORG_TYPES.get(self.event.config.get('org_type'), '')
        org_class = self.EntryForm.ORG_CLASSES.get(self.event.config.get('org_class'), '')
        return 'Affiliated with {} - a {} {}'.format(org_name, org_type, org_class)


class CommitteeMemberHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'COMMITTEE'
    NAME = 'Committee Member'

    class EntryForm(BaseEntryForm):

        CONFIG_FIELDS = [
            'committee_name',
            'committee_unit',
        ]

        committee_name = forms.CharField(label='Committee Name', max_length=255)
        committee_unit = forms.ModelChoiceField(label='Committee Unit', queryset=Unit.objects.all())

    def initialize(self):
        # TODO: Figure out a better way to do this
        unit_id = self.get_config('committee_unit')

        if unit_id is not None:
            self.set_config('committee_unit', Unit.objects.get(id=unit_id))

    def pre_save(self):
        # TODO: and this
        self.set_config('committee_unit', self.get_config('committee_unit').id)

    def post_save(self):
        # TODO: and also this.
        self.set_config('committee_unit', Unit.objects.get(id=self.get_config('committee_unit')))

    @property
    def default_title(self):
        return 'Joined a committee'

    def short_summary(self):
        return 'On the {} committee for the {}'.format(self.get_config('committee_name', ''),
                                                       self.get_config('committee_unit'))
