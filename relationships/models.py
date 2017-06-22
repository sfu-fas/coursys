from __future__ import unicode_literals
import datetime
import os

from django.db import models
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from autoslug import AutoSlugField

from coredata.models import Unit
from courselib.json_fields import JSONField, config_property
from courselib.slugs import make_slug

from .handlers import EmployerEvent, QuoteEvent, PhotoEvent, ResumeEvent

EVENT_HANDLERS = {
    'employer': EmployerEvent,
    'quote': QuoteEvent,
    'photo': PhotoEvent,
    'resume': ResumeEvent,
}
EVENT_CHOICES = [(key, cls) for key, cls in sorted(EVENT_HANDLERS.items())]


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
    event_type = models.CharField(max_length=10, choices=EVENT_CHOICES)
    timestamp = models.DateTimeField(default=datetime.datetime.now, editable=False)
    deleted = models.BooleanField(default=False)
    config = JSONField(default=dict)
    slug = AutoSlugField(populate_from='slug_string', unique_with=('contact',),
                         slugify=make_slug, null=False, editable=False)

    objects = IgnoreDeleted()

    @property
    def slug_string(self):
        return u'%s-%s' % (self.timestamp.year, self.event_type)

    @property
    def handler_class(self):
        return EVENT_HANDLERS[self.event_type]

    def save(self, call_from_handler=False, *args, **kwargs):
        assert call_from_handler, "A contact event must be saved through the handler."
        return super(Event, self).save(*args, **kwargs)

    def get_handler(self):
        # Create and return a handler for ourselves.  If we already created it, use the same one again.
        if not hasattr(self, 'handler_cache'):
            self.handler_cache = EVENT_HANDLERS.get(self.event_type, None)(self)
        return self.handler_cache


AttachmentSystemStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)


def attachment_upload_to(instance, filename):
    """
    callback to avoid path in the filename(that we have append folder structure to) being striped
    """
    fullpath = os.path.join(
        'relationships',
        instance.event.contact.unit.label,
        instance.event.contact.last_name,
        datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
        filename.encode('ascii', 'ignore'))
    return fullpath


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
    contents = models.FileField(storage=AttachmentSystemStorage, upload_to=attachment_upload_to, max_length=500)
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
