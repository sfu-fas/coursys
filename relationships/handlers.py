from django.utils.html import mark_safe
from django import forms
from django.template import Context, Template


class EventBase(object):
    name = ''
    event_type = ''
    TO_HTML_TEMPLATE = ''

    def __init__(self, event):
        self.event = event
        self.event.event_type = self.event_type

        # Figure out what fields are required by the Handler subclass
        cls.BASE_FIELDS = collections.OrderedDict()
        cls.CONFIG_FIELDS = collections.OrderedDict()

        for name, field in cls.EntryForm.base_fields.iteritems():
            if name in BaseEntryForm.base_fields:
                cls.BASE_FIELDS[name] = field
            else:
                cls.CONFIG_FIELDS[name] = field

    def to_html(self):
        """
        A detailed HTML presentation of this event
        """
        template = Template(self.TO_HTML_TEMPLATE)
        context = {
            'event': self.event,
            'handler': self,
        }
        return template.render(Context(context))

    @classmethod
    def create_for(cls, contact, form=None):
        """
        Given a contact, create a new instance of the handler for them.
        """
        from models import Event

        event = Event(contact=contact, event_type=cls.event_type)
        ret = cls(event)
        #  Add back if we decided to allow editing.
        # if form:
        #    ret.load(form)
        return ret


class CommentEventBase(EventBase):
    """
    Base class for events that are mostly a comment box.
    """
    name = ''
    event_type = ''
    TO_HTML_TEMPLATE = ''

    """"
    @property
    def form_class(self, event=None):
        return SomeFormClass(initial=event.data_as_dict_or_whatever())
    """

    def as_html(self):
        html = '<div>Event As HTML</div>'
        return mark_safe(html)


class FileEventBase(EventBase):
    """
    Base class for events that are mostly a file upload.
    """
    pass


class EmployerEvent(EventBase):
    name = 'Employer/Job'
    event_type = 'employer'


class QuoteEvent(CommentEventBase):
    name = 'Quote'
    event_type = 'quote'

    def as_html(self):
        return '{{ content|linebreaks }}'

    class EntryForm(forms.Form):
        content = forms.CharField(required=True, widget=forms.Textarea(attrs={'cols': 60, 'rows': 3}))


class PhotoEvent(FileEventBase):
    name = 'Photo'
    event_type = 'photo'

    class EntryForm(forms.Form):
        file = forms.FileField(required=True)
