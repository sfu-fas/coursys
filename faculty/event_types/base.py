import abc
import collections
import copy
import datetime
import itertools

from django import forms
from django.db import models
from django.forms.forms import pretty_name
from django.template import Context, Template

from coredata.models import Role, Unit

from faculty.event_types.constants import PERMISSION_LEVEL, PERMISSION_CHOICES
from faculty.event_types.fields import SemesterField
from faculty.event_types.fields import SemesterToDateField

ROLES = PERMISSION_CHOICES

SalaryAdjust = collections.namedtuple('SalaryAdjust', [
    'add_salary',
    'salary_fraction',
    'add_bonus',
])
TeachingAdjust = collections.namedtuple('TeachingAdjust', [
    'credits',
    'load_decrease',
])


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

        for name, field in cls.EntryForm.base_fields.iteritems():
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
    start_date = SemesterField(required=True, semester_start=True)
    end_date = SemesterField(required=False, semester_start=False)
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
        self.fields['unit'].choices = [(unicode(u.id), unicode(u)) for u in units]

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
        self.fields.keyOrder = [k for k in self.fields.keyOrder if k != 'comments']
        self.fields.keyOrder.append('comments')

        self.post_init()

    def post_init(self):
        "Hook to do setup of the form"
        pass


class CareerEventHandlerBase(object):

    __metaclass__ = CareerEventMeta

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

    def __init__(self, event):
        self.event = event

        # Just in case we add more complicated logic to __init__ we have to let subclasses easily
        # add initialization logic.
        self.initialize()

    def set_handler_specific_data(self):
        """
        Sets store Handler specific flags and type in the CareerEvent instance.

        """
        from faculty.models import CareerEvent
        self.event.event_type = self.EVENT_TYPE

        self.event.flags = 0
        for flag in self.FLAGS:
            self.event.flags |= getattr(CareerEvent.flags, flag)

    def save(self, editor):
        # TODO: Log the fact that `editor` made some changes to the CareerEvent.

        self.set_handler_specific_data()

        if self.IS_INSTANT:
            self.event.end_date = self.event.start_date

        self.pre_save()

        if self.IS_EXCLUSIVE:
            from faculty.models import CareerEvent
            previous_event = (CareerEvent.objects.filter(person=self.event.person,
                                                         unit=self.event.unit,
                                                         event_type=self.EVENT_TYPE,
                                                         start_date__lte=self.event.start_date,
                                                         end_date=None)
                                                 .order_by('start_date').last())
            if previous_event:
                previous_event.end_date = self.event.start_date - datetime.timedelta(days=1)
                previous_event.save(editor)

        self.event.save(editor)
        self.post_save()

    def get_config(self, name, default=None):
        raw_value = self.event.config.get(name)
        field = self.CONFIG_FIELDS[name]

        try:
            if raw_value is None:
                if default is not None:
                    return default
                else:
                    return field.to_python(field.initial)
            else:
                    return field.to_python(raw_value)
        except forms.ValidationError:
            # XXX: A hack to get around ChoiceField stuff. The idea is that if the value is in
            #      the config field, then it was most likely valid when the event was created.
            return raw_value

    def set_config(self, name, value):
        field = self.CONFIG_FIELDS[name]

        if isinstance(value, models.Model):
            raw_value = unicode(value.pk)
        else:
            raw_value = unicode(field.prepare_value(value))

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
        edit_units = set(r.unit for r in Role.objects.filter(person=editor, role='ADMN'))
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
        return form

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

    def to_timeline(self):
        """
        Returns a dictionary of the following format:
            {
                'startDate': '2014,2,27',
                'endDate': '2014,3,1',
                'headline': 'Testing',
                'text': '<p>some body</p>',
            }

        """
        payload = {
            'startDate': '{:%Y,%m,%d}'.format(self.event.start_date),
            'headline': self.short_summary(),
        }

        if self.event.end_date is not None:
            payload['endDate'] = '{:%Y,%m,%d}'.format(self.event.end_date)

        return payload

    # Stuff relating to searching

    @classmethod
    def get_search_rules(cls, data=None):
        return [(rule, rule.make_form(data)) for rule in cls.SEARCH_RULE_INSTANCES.itervalues()]

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


class Choices(collections.OrderedDict):
    '''
    An ordered dictionary that also acts as an iterable of (key, value) pairs.
    '''

    def __init__(self, *choices):
        super(Choices, self).__init__(choices)

    def __iter__(self):
        # XXX: Can't call super(Choices, self).iteritems() here because it will call our
        #      __iter__ and recurse infinitely.
        for key in super(Choices, self).__iter__():
            yield (key, self[key])
