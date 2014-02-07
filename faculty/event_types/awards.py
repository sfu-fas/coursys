import itertools, decimal, fractions

from django import forms

from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import SalaryAdjust, TeachingAdjust
from faculty.event_types.fields import DollarInput, AddSalaryField, AddPayField, TeachingCreditField
from faculty.event_types.mixins import TeachingCareerEvent, SalaryCareerEvent


class FellowshipEventHandler(CareerEventHandlerBase, SalaryCareerEvent, TeachingCareerEvent):
    """
    Appointment to a fellowship/chair
    """
    EVENT_TYPE = 'FELLOW'
    NAME = 'Fellowship / Chair'
    TO_HTML_TEMPLATE = """{% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Position</dt><dd>{{ position_display }}</dd>
        <dt>Add salary</dt><dd>${{ event|get_config:"add_salary"|floatformat:2 }}</dd>
        <dt>Add pay</dt><dd>${{ event|get_config:"add_pay"|floatformat:2 }}</dd>
        <dt>Teaching credit</dt><dd>{{ event|get_config:"teaching_credit" }} (per semester)</dd>
        {% endblock %}
        """

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

    def short_summary(self):
        pos = self.get_position_display()
        return "Appointment to %s" % (pos,)

    def to_html_context(self):
        return {'position_display': self.get_position_display()}

    def salary_adjust_annually(self):
        add_salary = decimal.Decimal(self.event.config.get('add_salary', 0))
        add_pay  = decimal.Decimal(self.event.config.get('add_pay', 0))
        return SalaryAdjust(add_salary, 1, add_pay)

    def teaching_adjust_per_semester(self):
        adjust = fractions.Fraction(self.event.config.get('teaching_credit', 0))
        return TeachingAdjust(adjust, adjust)

class AwardEventHandler(CareerEventHandlerBase):
    """
    Award Career event
    """
    EVENT_TYPE = 'AWARD'
    NAME = "Award Received"
    IS_INSTANT = True
    TO_HTML_TEMPLATE = """{% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Award</dt><dd>{{ event|get_config:"award"}}</dd>
        <dt>Awarded By</dt><dd>{{ event|get_config:"awarded_by" }}</dd>
        <dt>Amount</dt><dd>${{ event|get_config:"amount" }}</dd>
        <dt>Externally Funded?</dt><dd>{{ event|get_config:"externally_funded"|yesno }}</dd>
        <dt>In Payroll?</dt><dd>{{ event|get_config:"in_payroll"|yesno }}</dd>
        {% endblock %}
        """

    class EntryForm(BaseEntryForm):
        CONFIG_FIELDS = ['award', 'awarded_by', 'amount', 'externally_funded', 'in_payroll']
        award = forms.CharField(label='Award Name', max_length=255) 
        awarded_by = forms.CharField(label='Awarded By', max_length=255)
        amount = forms.DecimalField(widget=DollarInput, decimal_places=2, initial=0)
        externally_funded = forms.BooleanField(required=False)
        in_payroll = forms.BooleanField(required=False)


    @property
    def default_title(self):
        return 'Award Received'

    def short_summary(self):
        return 'Award: %s reveieved from %s' % (self.event.config.get('award', 0),
                                                self.event.config.get('awarded_by', 0))

class GrantApplicationEventHandler(CareerEventHandlerBase):
    """
    Grant Application Career event
    """
    EVENT_TYPE = 'GRANTAPP'
    NAME = "Grant Application"
    IS_INSTANT = True
    TO_HTML_TEMPLATE = """{% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Funding Agency</dt><dd>{{ event|get_config:"funding_agency"}}</dd>
        <dt>Grant Name</dt><dd>{{ event|get_config:"grant_name" }}</dd>
        <dt>Amount</dt><dd>${{ event|get_config:"amount" }}</dd>
        {% endblock %}
        """

    class EntryForm(BaseEntryForm):
        CONFIG_FIELDS = ['funding_agency', 'grant_name', 'amount']
        funding_agency = forms.CharField(label='Funding Agency', max_length=255)
        grant_name = forms.CharField(label='Grant Name', max_length=255)
        amount = forms.DecimalField(widget=DollarInput, decimal_places=2, initial=0)

    @property
    def default_title(self):
        return 'Applied for Grant'

    def short_summary(self):
        return 'Applied to %s for Grant: %s  for the amount of %s' % (self.event.config.get('funding_agency', 0),
                                                                    self.event.config.get('grant_name', 0),
                                                                    self.event.config.get('amount', 0))



