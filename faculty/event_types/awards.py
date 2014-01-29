import itertools

from django import forms

from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import BaseEntryForm


class FellowshipEventHandler(CareerEventHandlerBase):
    """
    Appointment to a fellowship/chair
    """
    EVENT_TYPE = 'FELLOW'
    NAME = 'Fellowship / Chair'
    TO_HTML_TEMPLATE = "{{ event.person.name }}'s event {{ handler.short_summary }}"

    class EntryForm(BaseEntryForm):
        CONFIG_FIELDS = ['position']
        position = forms.ChoiceField(required=True, choices=[])

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
                raise forms.ValidationError, "Couldn't check unit for fellowship ownership."

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
                raise forms.ValidationError, "That fellowship is not owned by the selected unit."

            return data

    @property
    def default_title(self):
        return 'Fellowship / Chair'

    def short_summary(self):
        from faculty.models import EventConfig
        ec = EventConfig.objects.get(unit=self.event.unit, event_type=self.key)
        fellowships = dict(ec.config.get('fellowships', []))

        return "Appointment to %s" % (fellowships[self.event.config['position']])
