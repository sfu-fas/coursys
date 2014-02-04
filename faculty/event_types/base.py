import abc
import collections
import copy
import datetime
import fractions
import itertools

from django import forms
from django.template import Context, Template

from coredata.models import Role, Unit

from faculty.event_types.constants import PERMISSION_LEVEL

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

        # Make a new list so we don't accidentally reference the base class' FLAGS
        cls.FLAGS = copy.copy(cls.FLAGS)

        for base in bases:
            # Add the flags from every mixin base class
            if hasattr(base, 'FLAGS'):
                for flag in base.FLAGS:
                    if flag not in cls.FLAGS:
                        cls.FLAGS.append(flag)


class BaseEntryForm(forms.Form):
    CONFIG_FIELDS = []
    title = forms.CharField(max_length=80, required=True, widget=forms.TextInput(attrs={'size': 60}))
    start_date = forms.DateField(required=True)
    end_date = forms.DateField(required=False)
    comments = forms.CharField(required=False,
                               widget=forms.Textarea(attrs={'cols': 60, 'rows': 3}))
    unit = forms.ModelChoiceField(queryset=Unit.objects.none(), required=True)

    def __init__(self, event, editor, units, *args, **kwargs):
        super(BaseEntryForm, self).__init__(*args, **kwargs)
        self.event = event
        self.editor = editor
        self.units = units
        self.fields['unit'].queryset = Unit.objects.filter(id__in=(u.id for u in units))
        self.fields['unit'].choices = [(unicode(u.id), unicode(u)) for u in units]

        if event.id:
            # it's already in the database, so load existing values as defaults
            # TODO: should this be done differently?
            self.initial['title'] = self.event.title
            self.initial['start_date'] = self.event.start_date
            self.initial['end_date'] = self.event.end_date
            self.initial['unit'] = self.event.unit
            self.initial['comments'] = self.event.comments
            for f in self.CONFIG_FIELDS:
                self.initial[f] = self.event.config.get(f, None)

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
    SEMESTER_BIAS = False

    VIEWABLE_BY = 'MEMB'
    EDITABLE_BY = 'DEPT'
    APPROVAL_BY = 'FAC'

    # Internal mumbo jumbo

    FLAGS = []

    def __init__(self, event):
        self.event = event
        assert len(self.EVENT_TYPE) < 10

        # Just in case we add more complicated logic to __init__ we have to let subclasses easily
        # add initialization logic.
        self.initialize()

    def save(self, editor):
        # TODO: Log the fact that `editor` made some changes to the CareerEvent.

        if self.IS_INSTANT:
            self.event.end_date = self.event.start_date

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

        self.pre_save()

        # TODO: store handler flags in the CareerEvent instance
        self.event.event_type = self.EVENT_TYPE
        self.event.save(editor)

        self.post_save()

    def get_config(self, key, default=None):
        return self.event.config.get(key, default)

    def set_config(self, key, value):
        self.event.config[key] = value

    # Other ways to create a new handler instance

    @classmethod
    def create_for(cls, person, unit):
        """
        Given a person, create a new instance of the handler for them.
        """
        from faculty.models import CareerEvent
        event = CareerEvent(person=person,
                            event_type=cls.EVENT_TYPE)
        if unit:
            event.unit = unit
        return cls(event)

    # Stuff involving permissions

    def permission(self, editor):
        """
        This editor's permission level with respect to this faculty member.
        """
        edit_units = set(r.unit for r in Role.objects.filter(person=editor, role='ADMN'))
        fac_units = set(r.unit for r in Role.objects.filter(person=self.event.person, role='FAC'))
        super_units = set(itertools.chain(*(u.super_units() for u in fac_units)))

        if editor == self.event.person:
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

    def can_view(self, editor):
        """
        Can the given user (a coredata.Person) can view the
        CareerEventType for this faculty member?
        """
        return self.has_permission(self.VIEWABLE_BY, editor)

    def can_edit(self, editor):
        """
        Can the given editor (a coredata.Person) can create/edit this
        CareerEventType for this faculty member?
        """
        return self.has_permission(self.EDITABLE_BY, editor)

    def can_approve(self, editor):
        """
        Can the given editor (a coredata.Person) can approve this
        CareerEventType for this faculty member?
        """
        return self.has_permission(self.APPROVAL_BY, editor)

    # Stuff relating to forms

    class EntryForm(BaseEntryForm):
        pass

    def load_from(self, form):
        """
        Given a valid form, load its data into the handler.
        """
        self.event.unit = form.cleaned_data['unit']
        self.event.event_type = self.EVENT_TYPE
        self.event.title = form.cleaned_data['title']
        self.event.start_date = form.cleaned_data['start_date']
        self.event.end_date = form.cleaned_data.get('end_date', None)
        self.event.comments = form.cleaned_data.get('comments', None)
        self.event.status = form.cleaned_data.get('status', 'NA')

        # XXX: status field: choose highest possible value for the available unit(s)?

        for field in form.CONFIG_FIELDS:
            data = form.cleaned_data[field]
            if isinstance(data, fractions.Fraction):
                data = unicode(data)
            self.event.config[field] = data

        return self.event

    def get_entry_form(self, editor, units, **kwargs):
        """
        Return a Django Form that can be used to create/edit a CareerEvent
        """
        initial = {
            'title': self.default_title,
            'start_date': datetime.date.today(),
        }
        form = self.EntryForm(event=self.event,
                              editor=editor,
                              units=units,
                              initial=initial,
                              **kwargs)

        if self.IS_INSTANT:
            del form.fields['end_date']

        return form

    def to_html(self):
        """
        A detailed HTML presentation of this event
        """
        template = Template(self.TO_HTML_TEMPLATE)
        context = {
            'event': self.event,
            'handler': self,
        }
        context.update(self.to_html_context())
        return template.render(Context(context))

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

    @property
    def default_title(self):
        return self.NAME

    # Override these

    @abc.abstractmethod
    def short_summary(self):
        """
        A short-line text-only summary of the event for summary displays

        """
        pass

    def to_html_context(self):
        """
        Additional context for the TO_HTML_TEMPLATE
        """
        return {}


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
