import abc
import datetime
import itertools

from django import forms
from django.template import Context, Template

from coredata.models import Role, Unit

from faculty.event_types.constants import PERMISSION_LEVEL


class CareerEventMeta(abc.ABCMeta):

    def __init__(cls, name, bases, members):
        super(CareerEventMeta, cls).__init__(name, bases, members)

        for base in bases:
            if hasattr(base, 'FLAGS'):
                cls.FLAGS.extend(base.FLAGS)
            if hasattr(base, 'HOOKS'):
                cls.HOOKS.extend(base.HOOKS)


class BaseEntryForm(forms.Form):
    # TODO: should this be a ModelForm for a CareerEvent? We'll have a circular import if so.
    CONFIG_FIELDS = []
    title = forms.CharField(max_length=80, required=True)
    start_date = forms.DateField(required=True)
    end_date = forms.DateField(required=False)
    #comments = forms.CharField(widget=forms.Textarea(), required=False)
    # TODO: changed from Unit.objects.none(), needed to populate the values in faculty.views.create_event
    unit = forms.ModelChoiceField(queryset=Unit.objects.all())


class CareerEventHandlerBase(object):

    __metaclass__ = CareerEventMeta

    HOOKS = []
    FLAGS = []

    DEFAULT_TITLE = ''
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
        self.event.save()

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
                            unit=unit,
                            event_type=cls.EVENT_TYPE)
        return cls(event)

    @classmethod
    def create_from(cls, person, form):
        """
        Given a form, create a new instance of the handler.

        """
        from faculty.models import CareerEvent
        event = CareerEvent(person=form.cleaned_data['person'],
                            unit=form.cleaned_data['unit'],
                            event_type=cls.EVENT_TYPE,
                            title=form.cleaned_data['title'],
                            start_date=form.cleaned_data['start_date'],
                            end_date=form.cleaned_data.get('end_date', None),
                            comments=form.cleaned_data.get('comments', None),
                            status=form.cleaned_data.get('status', 'NA'))

        # XXX: status field: choose highest possible value for the available unit(s)?

        for field in form.CONFIG_FIELDS:
            # TODO: Do some type checking or something
            event.config[field] = form.cleaned_data[field]

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

    def _apply_hooks_to_entry_form(self, form):
        for hook in self.hooks:
            hook.modify_entry_form(form)

    def get_entry_form(self, **kwargs):
        """
        Return a Django Form that can be used to create/edit a CareerEvent
        """
        units = kwargs.pop('units')
        initial = {
            'title': self.DEFAULT_TITLE,
            'start_date': datetime.date.today(),
        }

        form = self.EntryForm(initial=initial, **kwargs)

        # Apply hooks
        self._apply_hooks_to_entry_form(form)

        if units:
            form.fields['unit'].choices = units

        return form

    # Stuff relating to presentation

    def to_html(self):
        """
        A detailed HTML presentation of this event

        """
        template = Template(self.TO_HTML_TEMPLATE)
        context = Context({
            'event': self.event,
            'handler': self,
            'faculty': self.faculty,
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

    # Override these

    @abc.abstractmethod
    def short_summary(self):
        """
        A short-line text-only summary of the event for summary displays

        """
        pass
