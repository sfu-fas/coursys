import itertools, decimal, fractions

from django import forms

from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import SalaryAdjust, TeachingAdjust
from faculty.event_types.fields import AddSalaryField, AddPayField, TeachingCreditField
from faculty.event_types.mixins import TeachingCareerEvent, SalaryCareerEvent


class FellowshipEventHandler(CareerEventHandlerBase, SalaryCareerEvent, TeachingCareerEvent):
    """
    Appointment to a fellowship/chair
    """
    EVENT_TYPE = 'FELLOW'
    NAME = 'Fellowship / Chair'
    TO_HTML_TEMPLATE = "{{ event.person.name }}'s event {{ handler.short_summary }}"

    class EntryForm(BaseEntryForm):
        CONFIG_FIELDS = ['position', 'add_salary', 'add_pay', 'teaching_credit']
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
        try:
            ec = EventConfig.objects.get(unit=self.event.unit, event_type=self.EVENT_TYPE)
            fellowships = dict(ec.config.get('fellowships', []))
        except EventConfig.DoesNotExist:
            fellowships = {}

        pos = self.event.config.get('position', '???')
        return "Appointment to %s" % (fellowships.get(pos, pos))

    def salary_adjust_annually(self):
        add_salary = decimal.Decimal(self.event.config.get('add_salary', 0))
        add_pay  = decimal.Decimal(self.event.config.get('add_pay', 0))
        return SalaryAdjust(add_salary, 1, add_pay)

    def teaching_adjust_per_semester(self):
        adjust = fractions.Fraction(self.event.config.get('teaching_credit', 0))
        return TeachingAdjust(adjust, adjust)



