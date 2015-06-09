import fractions, itertools

from django import forms
from django.template import Context, Template

from coredata.models import Unit

from faculty.event_types import fields, search
from faculty.event_types.base import BaseEntryForm
from faculty.event_types.base import CareerEventHandlerBase
from faculty.event_types.choices import Choices
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

    def short_summary(self):
        org_name = self.get_config('org_name')
        return 'Affiliated with {}'.format(org_name)


class CommitteeMemberHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'COMMITTEE'
    NAME = 'Committee Member'
    config_name = 'Committee'

    TO_HTML_TEMPLATE = '''
        {% extends 'faculty/event_base.html' %}{% load event_display %}{% block dl %}
        <dt>Committee Name</dt><dd>{{ handler|get_display:'committee_name' }}</dd>
        <dt>Committee Unit</dt><dd>{{ handler|get_display:'committee_unit' }}</dd>
        <dt>Committee</dt><dd>{{ handler|get_display:'committee' }}</dd>
        {% endblock %}
    '''

    class EntryForm(BaseEntryForm):
        # committee_name and committee_unit were entered on some events before the configuration system was set up.
        # They will be migrated once the new system is in place.
        #committee_name = forms.CharField(label='Committee Name', max_length=255)
        #committee_unit = forms.ModelChoiceField(label='Committee Unit',
        #                                        queryset=Unit.objects.all())
        committee = forms.ChoiceField(label='Committee', choices=[])

        def post_init(self):
            # set the allowed position choices from the config from allowed units
            choices = CommitteeMemberHandler.get_committee_choices(self.units, only_active=True)
            self.fields['committee'].choices = choices

    @classmethod
    def get_committee_choices(cls, units, only_active=False):
        """
        Get the committee choices from EventConfig in these units, or superunits of them.
        """
        from faculty.models import EventConfig
        unit_lookup = dict((str(u.id), u) for u in Unit.objects.all())

        superunits = [u.super_units() for u in units] + [units]
        superunits =  set(u for sublist in superunits for u in sublist) # flatten list of lists
        ecs = EventConfig.objects.filter(unit__in=superunits,
                                         event_type=CommitteeMemberHandler.EVENT_TYPE)
        choices = itertools.chain(*[ec.config.get('committees', []) for ec in ecs])
        choices = (c for c in choices if c[-1] == 'ACTIVE')
        choices = ((short, '%s (%s)' % (long, unit_lookup[unit].label)) for short,long,unit,status in choices)
        return choices

    SEARCH_RULES = {
        'committee_name': search.StringSearchRule,
        'committee_unit': search.ChoiceSearchRule,
    }
    SEARCH_RESULT_FIELDS = [
        'committee',
    ]

    def get_display(self, field):
        if field in ['committee_name', 'committee_unit']:
            if field in self.event.config:
                return self.event.config[field]
            else:
                return '*obs*'
        else:
            return super(CommitteeMemberHandler, self).get_display(field)

    class ConfigItemForm(CareerEventHandlerBase.ConfigItemForm):
        flag_short = forms.CharField(label='Committee short form', help_text='e.g. UGRAD')
        flag = forms.CharField(label='Committee full name', help_text='e.g. Undergraduate Program Committee')
        ctte_unit = forms.ChoiceField(label="Committee Unit", help_text='Unit where the committee lives')

        def __init__(self, units, *args, **kwargs):
            super(CommitteeMemberHandler.ConfigItemForm, self).__init__(units, *args, **kwargs)
            unit_choices = [(u.id, u.name) for u in Unit.objects.all()]
            self.fields['ctte_unit'].choices = unit_choices

        def clean_flag_short(self):
            """
            Make sure the flag is globally-unique.
            """
            flag_short = self.cleaned_data['flag_short']
            CommitteeMemberHandler.ConfigItemForm.check_unique_key('COMMITTEE', 'committees', flag_short, 'committee')
            return flag_short

        def save_config(self):
            from faculty.models import EventConfig
            ec, _ = EventConfig.objects.get_or_create(unit=self.unit_object, event_type='COMMITTEE')
            fellows = ec.config.get('committees', [])
            fellows.append([self.cleaned_data['flag_short'], self.cleaned_data['flag'], self.cleaned_data['ctte_unit'], 'ACTIVE'])
            ec.config['committees'] = fellows
            ec.save()

    DISPLAY_TEMPLATE = Template("""
        <h2 id="config">Configured Committees</h2>
        <table class="display" id="config_table">
        <thead><tr><th scope="col">Committee Name</th><th scope="col">Committee Unit</th><th scope="col">Member Unit</th><!--<th scope="col">Action</th>--></tr></thead>
        <tbody>
            {% for unit, short, name, ctteunit, active in committees %}
            {% if active == 'ACTIVE' %}
            <tr>
                <td>{{ name }}</td>
                <td>{{ ctteunit.informal_name }}</td>
                <td>{{ unit.informal_name }}</td>
                <!--<td><a href="{ url 'faculty.views.delete_event_flag' event_type=event_type_slug unit=unit.label flag=short }">Delete</a></td>-->
            </tr>
            {% endif %}
            {% endfor %}
        </tbody>
        </table>""")

    @classmethod
    def config_display(cls, units):
        committees = list(cls.all_config_fields(Unit.sub_units(units), 'committees'))
        unit_lookup = dict((str(u.id), u) for u in Unit.objects.all())
        for c in committees:
            c[3] = unit_lookup[c[3]]
        context = Context({'committees': committees})
        return cls.DISPLAY_TEMPLATE.render(context)

    def get_committee_unit_display(self):
        unit = self.get_config('committee_unit', '')
        if unit:
            return unit.informal_name()
        else:
            return '???'

    def get_committee_unit_display_short(self):
        unit_id = self.event.config.get('committee_unit', None)
        unit = Unit.objects.get(id=unit_id)
        if unit:
            return unit.label
        else:
            return '???'

    def get_committee_display_short(self):
        choices = dict(
            self.get_committee_choices(
                self.event.unit.super_units(include_self=True)
            )
        )
        ctte = choices.get(self.get_config('committee', 'unknown committee'))
        return ctte

    def short_summary(self):
        if 'committee_name' in self.event.config:
            name = self.event.config.get('committee_name', '')
            unit = self.get_committee_unit_display_short()
            return 'Committee member: {} ({})'.format(name, unit)
        else:
            ctte = self.get_committee_display_short()
            return 'Committee member: {}'.format(ctte)

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

    def short_summary(self):
        return 'Member of {}'.format(self.get_config('lab_name'))


class ExternalServiceHandler(CareerEventHandlerBase, SalaryCareerEvent, TeachingCareerEvent):
    """
    External Service
    """

    EVENT_TYPE = 'EXTSERVICE'
    NAME = "External Service"

    TO_HTML_TEMPLATE = """
        {% extends "faculty/event_base.html" %}{% load event_display %}{% block dl %}
        <dt>Description</dt><dd>{{ handler|get_display:"description" }}</dd>
        <dt>Add Pay</dt><dd>${{ handler|get_display:"add_pay" }}</dd>
        <dt>Teaching Credits</dt><dd>{{ handler|get_display:"teaching_credits" }}</dd>
        {% endblock %}
    """

    class EntryForm(BaseEntryForm):
        description = forms.CharField(help_text='A brief description of the service', max_length=30)
        add_pay = fields.AddPayField()
        teaching_credits = fields.TeachingCreditField()

    def short_summary(self):
        return 'External Service: %s' % (self.get_config('description'))

    def salary_adjust_annually(self):
        add_pay = self.get_config('add_pay')
        return SalaryAdjust(0, 1, add_pay)

    def teaching_adjust_per_semester(self):
        credits = self.get_config('teaching_credits')
        return TeachingAdjust(credits, fractions.Fraction(0))


class SpecialDealHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'SPCL_DEAL'
    NAME = 'Special Deal'

    class EntryForm(BaseEntryForm):
        description = forms.CharField(help_text='A brief description of the deal', max_length=30)
        def post_init(self):
            self.fields['comments'].help_text = 'Enter details about the special deal.'
            self.fields['comments'].required = True

    def short_summary(self):
        return 'Special Deal: {}'.format(self.get_config('description'))

class OtherEventHandler(CareerEventHandlerBase):

    EVENT_TYPE = 'OTHER_NOTE'
    NAME = 'Other Event / Note'

    class EntryForm(BaseEntryForm):

        def post_init(self):
            self.fields['comments'].help_text = 'Enter details about the event or note here.'
            self.fields['comments'].required = True

    def short_summary(self):
        return 'Other Event / Note'
