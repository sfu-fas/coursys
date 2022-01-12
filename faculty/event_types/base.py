import abc
import collections
import copy
import datetime
import itertools

from django import forms
from django.db import models
from django.forms.utils import pretty_name
from django.template import Context, Template

from coredata.models import Role, Unit

from faculty.event_types.constants import PERMISSION_LEVEL, PERMISSION_CHOICES
from faculty.event_types.fields import SemesterField
from faculty.event_types.fields import SemesterToDateField
from faculty.util import ReportingSemester

ROLES = PERMISSION_CHOICES

SalaryAdjust = collections.namedtuple('SalaryAdjust', [
    'add_salary',
    'salary_fraction',
    'add_bonus',
])
SalaryAdjustIdentity = SalaryAdjust(0, 1, 0)
TeachingAdjust = collections.namedtuple('TeachingAdjust', [
    'credits',
    'load_decrease',
])
TeachingAdjustIdentity = TeachingAdjust(0, 0)

class CareerEventMeta(abc.ABCMeta):

    def __init__(cls, name, bases, members):
        super(CareerEventMeta, cls).__init__(name, bases, members)

        # Some integrity checks
        if not len(cls.EVENT_TYPE) <= 10:
            raise ValueError('{}.EVENT_TYPE is too long'.format(name))

        # Make a new list so we don't accidentally reference the base class' FLAGS
        cls.FLAGS = copy.copy(cls.FLAGS)

        for base in bases:
            # Add the flags from every mixin base class
            if hasattr(base, 'FLAGS'):
                for flag in base.FLAGS:
                    if flag not in cls.FLAGS:
                        cls.FLAGS.append(flag)

        # Modify the form accoding to our flags
        if cls.SEMESTER_PINNED:
            cls.EntryForm.base_fields['start_date'] = SemesterToDateField(start=True)
            cls.EntryForm.base_fields['end_date'] = SemesterToDateField(start=False,
                                                                        required=False)
        else:
            # NOTE: We don't allow IS_INSTANT to work with SEMESTER_PINNED
            # If IS_INSTANT, get rid of the 'end_date' field from EntryForm
            if cls.IS_INSTANT and 'end_date' in cls.EntryForm.base_fields:
                del cls.EntryForm.base_fields['end_date']

        # Figure out what fields are required by the Handler subclass
        cls.BASE_FIELDS = collections.OrderedDict()
        cls.CONFIG_FIELDS = collections.OrderedDict()

        for name, field in cls.EntryForm.base_fields.items():
            if name in BaseEntryForm.base_fields:
                cls.BASE_FIELDS[name] = field
            else:
                cls.CONFIG_FIELDS[name] = field

        # Instantiate each of the SearchRules
        cls.SEARCH_RULE_INSTANCES = collections.OrderedDict()

        for name in cls.CONFIG_FIELDS:
            if name in cls.SEARCH_RULES:
                field = cls.CONFIG_FIELDS[name]
                cls.SEARCH_RULE_INSTANCES[name] = cls.SEARCH_RULES[name](name, field, cls)


class BaseEntryForm(forms.Form):
    start_date = SemesterField(required=True, semester_start=True, help_text="Day this becomes effective: enter date or enter semester code on the right")
    end_date = SemesterField(required=False, semester_start=False, help_text="Day this ends: enter date or enter semester code on the right")
    comments = forms.CharField(required=False,
                               widget=forms.Textarea(attrs={'cols': 60, 'rows': 3}))
    unit = forms.ModelChoiceField(queryset=Unit.objects.none(), required=True)

    def __init__(self, editor, units, *args, **kwargs):
        handler = kwargs.pop('handler', None)
        self.person = kwargs.pop('person', None)
        self.editor = editor
        self.units = units
        super(BaseEntryForm, self).__init__(*args, **kwargs)

        self.fields['unit'].queryset = Unit.objects.filter(id__in=(u.id for u in units))
        self.fields['unit'].choices = [(str(u.id), str(u)) for u in units]

        # Load initial data from the handler instance if possible
        if handler:
            self.initial['start_date'] = handler.event.start_date
            self.initial['end_date'] = handler.event.end_date
            self.initial['unit'] = handler.event.unit
            self.initial['comments'] = handler.event.comments

            # Load any handler specific field values
            for name in handler.CONFIG_FIELDS:
                self.initial[name] = handler.get_config(name, None)

        # force the comments field to the bottom
        comments = self.fields.pop('comments')
        self.fields['comments'] = comments

        self.post_init()

    def post_init(self):
        "Hook to do setup of the form"
        pass

    def clean_end_date(self):
        start_date = self.cleaned_data.get('start_date', None)
        end_date = self.cleaned_data['end_date']
        if not start_date:
            return end_date
        if not end_date:
            return
        if start_date > end_date:
            raise forms.ValidationError('End date cannot be before the start date.')
        return end_date


class CareerEventHandlerBase(object, metaclass=CareerEventMeta):

    NAME = ''
    EVENT_TYPE = ''

    TO_HTML_TEMPLATE = """{% extends "faculty/event_base.html" %}"""

    # Event has no duration (start_date is set to end_date automagically)
    IS_INSTANT = False
    # There can only be one (with same person, unit, event_type without an end_date)
    IS_EXCLUSIVE = False
    # Show a semester selection widget for start/end date instead of a raw date picker
    SEMESTER_PINNED = False

    VIEWABLE_BY = 'MEMB'
    EDITABLE_BY = 'DEPT'
    APPROVAL_BY = 'FAC'

    SEARCH_RULES = {}
    SEARCH_RESULT_FIELDS = []

    # Internal mumbo jumbo

    BASE_FIELDS = {}
    CONFIG_FIELDS = {}
    SEARCH_RULE_INSTANCES = []
    FLAGS = []
    PDFS = {}

    # A dict for extra links to display in the template.  Should only be populated in the derived classes if needed.
    EXTRA_LINKS = {}

    def __init__(self, event):
        self.event = event

        # Just in case we add more complicated logic to __init__ we have to let subclasses easily
        # add initialization logic.
        self.initialize()

    def set_handler_specific_data(self):
        """
        Sets store Handler specific flags and type in the CareerEvent instance.
        """
        self.event.event_type = self.EVENT_TYPE

        self.event.flags = 0
        # only set the flags in the event if they have a non-identity value: i.e. they actually *do* affect something
        self.event.flags.affects_salary = ('affects_salary' in self.FLAGS
                                           and SalaryAdjustIdentity != self.salary_adjust_annually())
        self.event.flags.affects_teaching = ('affects_teaching' in self.FLAGS
                                             and TeachingAdjustIdentity != self.teaching_adjust_per_semester())

    def neaten_exclusive_end_dates(self, editor):
        """
        Tidy up the end dates of exclusive events: at least closes and previous open events, but also handles
        the case of events being entered out-of-order.
        """
        assert self.IS_EXCLUSIVE and not self.IS_INSTANT
        from faculty.models import CareerEvent

        similar_events = CareerEvent.objects.not_deleted().filter(person=self.event.person,
                unit=self.event.unit, event_type=self.EVENT_TYPE).order_by('start_date')
        similar_events = list(similar_events)
        for event, next_event in zip(similar_events, similar_events[1:]):
            event.end_date = next_event.start_date - datetime.timedelta(days=1)
            event.save(editor, call_from_handler=True)

    def save(self, editor):
        # TODO: Log the fact that `editor` made some changes to the CareerEvent.
        self.set_handler_specific_data()

        if self.IS_INSTANT:
            self.event.end_date = self.event.start_date

        self.pre_save()
        self.event.save(editor, call_from_handler=True)

        if self.IS_EXCLUSIVE:
            self.neaten_exclusive_end_dates(editor)

        if self.event.event_type == 'SALARY':
            # invalidate cache of rank
            from faculty.models import CareerEvent
            CareerEvent.current_ranks.invalidate(self.event.person.id)

        self.post_save()

    def get_config(self, name, default=None):
        raw_value = self.event.config.get(name)
        field = self.CONFIG_FIELDS[name]

        try:
            if raw_value is None:
                if field.initial is not None and field.initial != '':
                    return field.to_python(field.initial)
                else:
                    return default
            else:
                return field.to_python(raw_value)
        except forms.ValidationError:
            # XXX: A hack to get around ChoiceField stuff. The idea is that if the value is in
            #      the config field, then it was most likely valid when the event was created.
            return raw_value

    def set_config(self, name, value):
        field = self.CONFIG_FIELDS[name]
        if value is None:
            raw_value = None
        elif isinstance(value, models.Model):
            raw_value = str(value.pk)
        else:
            raw_value = str(field.prepare_value(value))

        self.event.config[name] = raw_value

    # Other ways to create a new handler instance

    @classmethod
    def create_for(cls, person, form=None):
        """
        Given a person, create a new instance of the handler for them.
        """
        from faculty.models import CareerEvent
        event = CareerEvent(person=person,
                            event_type=cls.EVENT_TYPE)
        ret = cls(event)
        if form:
            ret.load(form)
        return ret

    # Stuff involving permissions

    def permission(self, editor):
        """
        This editor's permission level with respect to this faculty member.
        """
        edit_units = set(r.unit for r in Role.objects_fresh.filter(person=editor, role__in=['ADMN', 'FACA']))
        fac_units = set()
        if self.event:
            fac_units = set(r.unit for r in Role.objects.filter(person=self.event.person, role='FAC'))
        super_units = set(itertools.chain(*(u.super_units() for u in fac_units)))

        if self.event and (editor == self.event.person):
            # first on purpose: don't let dept chairs approve/edit their own stuff
            return 'MEMB'
        elif edit_units & super_units:
            # give dean's office level permission to anybody above in the hierarchy:
            # not technically correct, but correct in practice.
            return 'FAC'
        elif edit_units & fac_units:
            return 'DEPT'
        else:
            return 'NONE'

    def has_permission(self, perm, editor):
        """
        Does the given editor (a coredata.Person) have this permission
        for this faculty member?

        Implemented as a method so we can override or extend if necessary.
        """
        permission = self.permission(editor)
        return PERMISSION_LEVEL[permission] >= PERMISSION_LEVEL[perm]

    def get_view_role(self):
        return ROLES[self.VIEWABLE_BY]

    def can_view(self, editor):
        """
        Can the given user (a coredata.Person) can view the
        CareerEventType for this faculty member?
        """
        return self.has_permission(self.VIEWABLE_BY, editor)

    def get_edit_role(self):
        return ROLES[self.EDITABLE_BY]

    def can_edit(self, editor):
        """
        Can the given editor (a coredata.Person) can create/edit this
        CareerEventType for this faculty member?
        """
        return self.has_permission(self.EDITABLE_BY, editor)

    def get_approve_role(self):
        return ROLES[self.APPROVAL_BY]

    def can_approve(self, editor):
        """
        Can the given editor (a coredata.Person) can approve this
        CareerEventType for this faculty member?
        """
        return self.has_permission(self.APPROVAL_BY, editor)

    def set_status(self, editor):
        """
        Set status appropriate to the editor.  Override this method
        if the status checking becomes more complex for an event type.
        """
        if self.can_approve(editor):
            self.event.status = 'A'
            self.save(editor)
        else:
            self.event.status = 'NA'
            self.save(editor)

    # Stuff relating to forms

    class EntryForm(BaseEntryForm):
        pass

    def load(self, form):
        """
        Given a valid form, load its data into the handler.
        """
        try:
            self.event.unit = form.cleaned_data['unit']
            self.event.start_date = form.cleaned_data['start_date']
        except KeyError:
            pass

        self.event.end_date = form.cleaned_data.get('end_date', None)
        self.event.comments = form.cleaned_data.get('comments', None)
        # XXX: Event status is set based on the editor,
        # This is set in handler method 'set_status'
        # The following line causes bug which resets status to 'NA'
        # every time the form is loaded, this is not desired behavior.
        #self.event.status = form.cleaned_data.get('status', 'NA')

        for name in self.CONFIG_FIELDS:
            self.set_config(name, form.cleaned_data.get(name, None))

    @classmethod
    def get_entry_form(cls, editor, units, handler=None, person=None, **kwargs):
        """
        Return a Django Form that can be used to create/edit a CareerEvent
        """
        initial = {
            'start_date': datetime.date.today(),
        }
        form = cls.EntryForm(editor=editor,
                             units=units,
                             initial=initial,
                             handler=handler,
                             person=person,
                             **kwargs)
        form.legend = cls.NAME
        form.use_required_attribute = False
        return form

    # event configuration

    config_name = None

    class ConfigItemForm(forms.Form):
        unit = forms.ChoiceField(help_text='Unit that owns this option (faculty members within this unit will have '
                'this option presented)')

        def __init__(self, units, *args, **kwargs):
            super(CareerEventHandlerBase.ConfigItemForm, self).__init__(*args, **kwargs)
            unit_choices = [(u.id, u.name) for u in Unit.sub_units(units)]
            self.fields['unit'].choices = unit_choices

        def clean(self):
            data = self.cleaned_data
            # stash the unit object forward for save_config
            unit = Unit.objects.get(id=data['unit'])
            self.unit_object = unit
            return data

        @classmethod
        def check_unique_key(cls, event_type, config_key, value, config_name):
            """
            Check that this value is unique in EvenConfig[event_type~=event_type].config[config_key] first elements.
            """
            from faculty.models import EventConfig
            existing = itertools.chain.from_iterable(
                (f[0] for f in fl)
                for fl
                in (
                    ec.config.get(config_key, [])
                    for ec
                    in EventConfig.objects.filter(event_type=event_type)
                )
            )
            if value in existing:
                raise forms.ValidationError('This short form has been used by another %s: they must be unique.'
                        % (config_name,))

        def save_config(self):
            """
            Save the form to a config object owned by the selected unit.
            """
            raise NotImplementedError()

    @classmethod
    def get_config_item_form(cls, units, **kwargs):
        form = cls.ConfigItemForm(units=units, **kwargs)
        return form

    @classmethod
    def all_config_fields(cls, units, field):
        """
        Look up EventConfig.config[field] for each unit. Returns an iterable of [unit,] + config_val lists.
        """
        from faculty.models import EventConfig
        configs = EventConfig.objects.filter(unit__in=units, event_type=cls.EVENT_TYPE)
        unit_cfs = (([cfg.unit] + e for e in cfg.config.get(field, [])) for cfg in configs)
        return itertools.chain.from_iterable(unit_cfs)

    @classmethod
    def config_display(cls, units):
        """
        Get all of the configuration items for these units
        """
        return None

    # Stuff relating to HTML display

    def get_display(self, field, default='unknown'):
        """
        Returns the display value for a field.

        """
        display_func_name = 'get_{}_display'.format(field)
        if hasattr(self, display_func_name):
            return getattr(self, display_func_name)()
        else:
            return self.get_config(field, default)

    def to_html_context(self):
        """
        Additional context for the TO_HTML_TEMPLATE
        """
        return {}

    def to_html(self):
        """
        A detailed HTML presentation of this event
        """
        template = Template(self.TO_HTML_TEMPLATE)
        context = {
            'event': self.event,
            'handler': self,
            'start': self.event.start_date,
            'end': self.event.end_date,
        }
        context.update(self.to_html_context())
        return template.render(Context(context))

    # Stuff relating to searching

    @classmethod
    def get_search_rules(cls, viewer, member_units, data=None):
        return [(rule, rule.make_form(viewer, member_units, data))
                for rule in cls.SEARCH_RULE_INSTANCES.values()]

    @classmethod
    def validate_all_search(cls, rules):
        return not bool([False for _, form in rules if not form.is_valid()])

    @classmethod
    def filter(cls, events, rules=None, viewer=None):
        if not rules:
            rules = []

        for event in events:
            handler = cls(event)

            if viewer and not handler.can_view(viewer):
                continue

            for rule, form in rules:
                if not rule.matches(handler, form):
                    break
            else:
                yield handler

    @classmethod
    def get_search_columns(cls):
        return [cls.CONFIG_FIELDS[name].label or pretty_name(name) for name in cls.SEARCH_RESULT_FIELDS]

    def to_search_row(self):
        return [self.get_display(name) for name in self.SEARCH_RESULT_FIELDS]

    def semester_length(self):
        if self.event.end_date:
            rng = ReportingSemester.range(self.event.start_date, self.event.end_date)
        else:
            rng = ReportingSemester.range(self.event.start_date, datetime.date.today())
        return len(list(rng))

    # event config

    flag_config_key = None # if set, EventConfig.config[flag_config_key] should be a list of even flag tuples

    @classmethod
    def config_flags(cls, units):
        """
        Return a list of the event flag configuration options (for these units). Return None if not applicable.
        """
        if not cls.flag_config_key:
            return None

        from faculty.models import EventConfig
        ecs = EventConfig.objects.filter(event_type=cls.EVENT_TYPE, unit__in=units).select_related('unit')
        return [(ec.unit, ec.config.get(cls.flag_config_key, [])) for ec in ecs]

    # Optionally override these

    def initialize(self):
        pass

    def pre_save(self):
        '''
        Executed prior to saving the associated CareerEvent.

        '''
        pass

    def post_save(self):
        '''
        Executed after saving the associated CareerEvent.

        '''
        pass

    # Override these

    @abc.abstractmethod
    def short_summary(self):
        """
        A short-line text-only summary of the event for summary displays

        """
        pass

    def generate_pdf(self, key):
        """
        A method to generate a PDF from the PDF dictionary in the class.
        This needs to be implemented in each derived class that has extra PDFs.

        :param key: The key for the PDF from the handler's PDF list
        :type key: String
        :return: The PDF form
        :rtype: HttpResponse
        """
        raise NotImplementedError("This needs to be implemented in the derived class")




