import collections

from django import forms
from django.db import models
from django.template import Context, Template


class EventBase(object):
    name = ''
    event_type = ''
    TO_HTML_TEMPLATE = ''

    def __init__(self, event):
        self.event = event
        self.event.event_type = self.event_type

        # Figure out what fields are required by the Handler subclass
        self.CONFIG_FIELDS = collections.OrderedDict()

        for name, field in self.EntryForm.base_fields.iteritems():
            self.CONFIG_FIELDS[name] = field

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

    def save(self):
        self.event.save(call_from_handler=True)

    @classmethod
    def create_for(cls, contact, form=None):
        """
        Given a contact, create a new instance of the handler for them.
        """
        from models import Event

        event = Event(contact=contact, event_type=cls.event_type)
        ret = cls(event)
        ret.load(form)
        return ret

    def get_config(self, name, default=None):
        raw_value = self.event.config.get(name, default)
        field = self.CONFIG_FIELDS.get(name, None)

        # If the handler template is calling the wrong attribute, return None.
        if not (raw_value and field):
            return None

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
            raw_value = unicode(value.pk)
        else:
            raw_value = unicode(field.prepare_value(value))

        self.event.config[name] = raw_value

    def load(self, form):
        """
        Given a valid form, load its data into the handler.
        """
        for name in self.CONFIG_FIELDS:
            self.set_config(name, form.cleaned_data.get(name, None))


class CommentEventBase(EventBase):
    """
    Base class for events that are mostly a comment box.
    """
    name = ''
    event_type = ''

    TO_HTML_TEMPLATE = """{% load contact_display %}<div>
        {{ handler|get_event_value:'content'|linebreaks }}</div>"""

    class EntryForm(forms.Form):
        content = forms.CharField(required=True, widget=forms.Textarea(attrs={'cols': 60, 'rows': 3}))


class FileEventBase(EventBase):
    """
    Base class for events that are mostly a file upload.
    """
    class EntryForm(forms.Form):
        file = forms.FileField(required=True)

    @classmethod
    def add_attachment(cls, event, filedata):
        from models import EventAttachment
        print "Adding Attachment"
        upfile = filedata['file']
        filetype = upfile.content_type
        if upfile.charset:
            filetype += "; charset=" + upfile.charset
        mediatype = filetype
        attach = EventAttachment(event=event, mediatype=mediatype, contents=upfile)
        attach.save(call_from_handler=True)



class EmployerEvent(EventBase):
    name = 'Employer/Job'
    event_type = 'employer'


class QuoteEvent(CommentEventBase):
    name = 'Quote'
    event_type = 'quote'


class PhotoEvent(FileEventBase):
    name = 'Photo'
    event_type = 'photo'

class ResumeEvent(FileEventBase):
    name = 'Resume'
    event_type = 'resume'

