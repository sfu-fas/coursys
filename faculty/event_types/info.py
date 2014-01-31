from django import forms

from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import BaseEntryForm


class ExternalAffiliationHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'EXTERN_AFFIL'
    NAME = 'External Affilication'

    class EntryForm(BaseEntryForm):

        CONFIG_FIELDS = [
            'org_name',
            'org_type',
            'org_class',
            'is_research',
            'is_adjunct',
        ]
        ORG_TYPE_CHOICES = (
            ('SFU', 'Internal SFU'),
            ('ACADEMIC', 'Academic'),
            ('PRIVATE', 'Private Sector'),
        )
        ORG_CLASS_CHOICES = (
            ('EXTERN_COMP', 'External Company'),
            ('NO_PROFIT', 'Not-For-Profit'),
        )

        org_name = forms.CharField('Organization Name', max_length=255)
        org_type = forms.CharField('Organization Type', max_length=10, choices=ORG_TYPE_CHOICES)
        org_class = forms.CharField('Organization Classification', max_length=10,
                                    choices=ORG_CLASS_CHOICES)
        is_research = forms.BooleanField('Research Institute/Centre?', default=False)
        is_adjunct = forms.BooleanField('Adjunct?', default=False)

    @property
    def default_title(self):
        return 'Affiliated with {}'.format(self.event.config.get('org_name', ''))

    def short_summary(self):
        # TODO: Get the display names for org_type and org_class in a sane way.
        # TODO: Figure out a nicer format that includes all relevant information.
        return ('Affiliated with {} a ({}) instituation.'
                .format(self.event.config.get('org_name', ''),
                        self.event.config.get('org_type', '')))
