from __future__ import unicode_literals
import datetime
import os
import uuid

from django.db import models
from django.conf import settings
from autoslug import AutoSlugField

from coredata.models import Unit, Person
from courselib.json_fields import JSONField
from courselib.slugs import make_slug
from courselib.storage import UploadedFileStorage, upload_path

from .handlers import EmployerEvent, QuoteEvent, PhotoEvent, ResumeEvent, AcknowledgementEvent, AlumnusEvent, \
    AwardEvent, EACEvent, FacultyConnectionEvent, FieldEvent, FollowUpEvent, FundingEvent, \
    LinksEvent, NotesEvent, ParticipationEvent, PartnershipEvent, RelationshipEvent

EVENT_HANDLERS = [
    EmployerEvent,
    QuoteEvent,
    PhotoEvent,
    ResumeEvent,
    AcknowledgementEvent,
    AlumnusEvent,
    AwardEvent,
    EACEvent,
    FacultyConnectionEvent,
    FieldEvent,
    NotesEvent,
    FollowUpEvent,
    FundingEvent,
    LinksEvent,
    ParticipationEvent,
    PartnershipEvent,
    RelationshipEvent
]

EVENT_TYPES = {handler.event_type: handler for handler in EVENT_HANDLERS}
EVENT_CHOICES = [(cls.event_type, cls) for cls in sorted(EVENT_HANDLERS)]


class IgnoreDeleted(models.Manager):
    def get_queryset(self):
        return super(IgnoreDeleted, self).get_queryset().filter(deleted=False)


class Contact(models.Model):
    unit = models.ForeignKey(Unit, null=False, blank=False)
    slug = AutoSlugField(populate_from='slug_string', unique_with=('unit',),
                         slugify=make_slug, null=False, editable=False)
    title = models.CharField(max_length=4, null=True, blank=True)
    last_name = models.CharField(max_length=32)
    first_name = models.CharField(max_length=32)
    middle_name = models.CharField(max_length=32, null=True, blank=True)
    pref_first_name = models.CharField("Preferred First Name", max_length=32, null=True, blank=True)
    company_name = models.CharField(max_length=128, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=15, null=True, blank=True)
    deleted = models.BooleanField(default=False)
    config = JSONField(default=dict)

    objects = IgnoreDeleted()

    @property
    def slug_string(self):
        return u'%s %s %s' % (self.first_name, self.last_name, self.unit.label)

    def full_name(self):
        return u'%s, %s' % (self.last_name, self.first_name)

    def name(self):
        return u"%s %s" % (self.first_name, self.last_name)

    def __unicode__(self):
        return u'%s, %s' % (self.unit.label.upper(), self.full_name())


class Event(models.Model):
    contact = models.ForeignKey(Contact, null=False, blank=False)
    event_type = models.CharField(max_length=25, choices=EVENT_CHOICES)
    timestamp = models.DateTimeField(default=datetime.datetime.now, editable=False)
    last_modified = models.DateTimeField(null=True, blank=True, editable=False)
    last_modified_by = models.ForeignKey(Person, null=True, blank=True)
    deleted = models.BooleanField(default=False)
    config = JSONField(default=dict)
    slug = AutoSlugField(populate_from='slug_string', unique_with=('contact',),
                         slugify=make_slug, null=False, editable=False)

    objects = IgnoreDeleted()

    @property
    def slug_string(self):
        return u'%s-%s' % (self.timestamp.year, self.event_type)

    def save(self, call_from_handler=False, editor=None, *args, **kwargs):
        assert call_from_handler, "A contact event must be saved through the handler."
        self.last_modified = datetime.datetime.now()
        self.last_modified_by = editor
        return super(Event, self).save(*args, **kwargs)

    def get_handler(self):
        # Create and return a handler for ourselves.  If we already created it, use the same one again.
        if not hasattr(self, 'handler_cache'):
            self.handler_cache = EVENT_TYPES.get(self.event_type, None)(self)
        return self.handler_cache

    def get_handler_name(self):
        return self.get_handler().name

    def get_config_value(self, field):
        if field in self.config:
            return self.config.get(field)
        else:
            return None

    def is_text_based(self):
        return self.get_handler().text_content


def attachment_upload_to(instance, filename):
    return upload_path('relationships', str(instance.event.timestamp.year), filename)


class EventAttachmentManagerQuerySet(models.QuerySet):
    def visible(self):
        return self.filter(hidden=False)


class EventAttachment(models.Model):
    """
    Document attached to an Event. Let's assume that each event has exactly one attachment at most.
    These attachments will be created by our views if we add an event from the FileEventBase handler or its subclasses.
    """
    event = models.OneToOneField(Event, null=False, blank=False)
    slug = AutoSlugField(populate_from='mediatype', null=False, editable=False, unique_with=('event',))
    created_at = models.DateTimeField(auto_now_add=True)
    contents = models.FileField(storage=UploadedFileStorage, upload_to=attachment_upload_to, max_length=500)
    mediatype = models.CharField(max_length=200, null=True, blank=True, editable=False)
    hidden = models.BooleanField(default=False, editable=False)

    objects = EventAttachmentManagerQuerySet.as_manager()

    def __unicode__(self):
        return self.contents.name

    class Meta:
        ordering = ("created_at",)
        unique_together = (("event", "slug"),)

    def contents_filename(self):
        return os.path.basename(self.contents.name)

    def hide(self, call_from_handler=False):
        self.hidden = True
        self.save(call_from_handler=call_from_handler)

    def save(self, call_from_handler=False, *args, **kwargs):
        assert call_from_handler, "A contact event attachment must be saved through the handler."
        return super(EventAttachment, self).save(*args, **kwargs)
