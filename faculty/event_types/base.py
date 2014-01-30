import abc
import collections
import datetime
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

        for base in bases:
            if hasattr(base, 'FLAGS'):
                cls.FLAGS.extend(base.FLAGS)
            if hasattr(base, 'HOOKS'):
                cls.HOOKS.extend(base.HOOKS)


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

    HOOKS = []
    FLAGS = []

    NAME = ''
    EVENT_TYPE = ''

    # View / Edit flags
    VIEWABLE_BY = 'MEMB'
    EDITABLE_BY = 'DEPT'
    APPROVAL_BY = 'FAC'

    def __init__(self, event):
        self.hooks = [hook_class() for hook_class in self.HOOKS]

        # XXX: I think that creating the CareerEvent instance should be left up to the caller.
        self.event = event

        # Just in case we add more complicated logic to __init__ we have to let subclasses easily
        # add initialization logic.
        self.initialize()

    def pre_hook_save(self):
        for hook in self.hooks:
            hook.pre_save(self.event)

    def post_hook_save(self):
        for hook in self.hooks:
            hook.post_save(self.event)

    def save(self, editor):
        # TODO: Log the fact that `editor` made some changes to the CareerEvent.

        self.pre_save()
        self.pre_hook_save()

        # TODO: store handler flags in the CareerEvent instance
        self.event.event_type = self.EVENT_TYPE
        self.event.save(editor)

        self.post_hook_save()
        self.post_save()

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
        # XXX: Does _apply_hooks_to_entry_form(...) need to be run here?

        for field in form.CONFIG_FIELDS:
            # TODO: Do some type checking or something
            self.event.config[field] = form.cleaned_data[field]

        return self.event

    def _apply_hooks_to_entry_form(self, form):
        for hook in self.hooks:
            hook.modify_entry_form(form)

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

        # Apply hooks
        self._apply_hooks_to_entry_form(form)

        return form

    def to_html(self):
        """
        A detailed HTML presentation of this event

        """
        template = Template(self.TO_HTML_TEMPLATE)
        context = Context({
            'event': self.event,
            'handler': self,
        })
        return template.render(context)

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

