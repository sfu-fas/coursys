from django import forms

from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import Choices


class ExternalAffiliationHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'EXTERN_AFFIL'
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
