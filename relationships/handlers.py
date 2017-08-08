import collections

from django import forms
from django.db import models
from django.template import Context, Template


class EventBase(object):
    name = ''
    event_type = ''
    TO_HTML_TEMPLATE = ''
    text_content = False

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

    def save(self, editor=None):
        self.event.save(call_from_handler=True, editor=editor)

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

    def load_initial(self, form):
        # Load the data from the event into the form for editing
        for name in self.CONFIG_FIELDS:
            form.initial[name] = self.get_config(name, None)


class CommentEventBase(EventBase):
    """
    Base class for events that are mostly a comment box.
    """
    name = ''
    event_type = ''
    text_content = True

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
        upfile = filedata['file']
        filetype = upfile.content_type
        if upfile.charset:
            filetype += "; charset=" + upfile.charset
        mediatype = filetype
        attach = EventAttachment(event=event, mediatype=mediatype, contents=upfile)
        attach.save(call_from_handler=True)


class EmployerEvent(CommentEventBase):
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


class RelationshipEvent(CommentEventBase):
    name = 'Main Relationship Holder(s)'
    event_type = 'relationship'


class FacultyConnectionEvent(CommentEventBase):
    name = 'Faculty Connection'
    event_type = 'facultyconnection'


class LinksEvent(CommentEventBase):
    name = 'Links'
    event_type = 'links'


class FollowUpEvent(CommentEventBase):
    name = 'Follow-Up/Tasks'
    event_type = 'followups'


class AwardEvent(CommentEventBase):
    name = 'Awards'
    event_type = 'awards'


class FundingEvent(CommentEventBase):
    name = 'Funding/In-Kind Support'
    event_type = 'funding'


class PartnershipEvent(CommentEventBase):
    name = 'Partnership Interest'
    event_type = 'partnership'


class ParticipationEvent(CommentEventBase):
    name = 'Past Participation'
    event_type = 'participation'


class AcknowledgementEvent(CommentEventBase):
    name = 'Past Acknowledgements'
    event_type = 'acknowledgement'


class EACEvent(CommentEventBase):
    name = 'EAC Membership'
    event_type = 'eac'


class AlumnusEvent(CommentEventBase):
    name = 'SFU Alumnus'
    event_type = 'alumnus'


class FieldEvent(CommentEventBase):
    name = 'Field Background'
    event_type = 'field'

class NotesEvent(CommentEventBase):
    name = 'Notes'
    event_type = 'notes'