from __future__ import unicode_literals
import datetime

from django.db import models
from autoslug import AutoSlugField

from coredata.models import Unit
from courselib.json_fields import JSONField, config_property
from courselib.slugs import make_slug

from .handlers import EmployerEvent, QuoteEvent, PhotoEvent

EVENT_HANDLERS = {
    'employer': EmployerEvent,
    'quote': QuoteEvent,
    'photo': PhotoEvent,
}
EVENT_CHOICES = [(key, cls) for key, cls in EVENT_HANDLERS.items()]


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
    attachment = models.FileField(null=True, max_length=500)  # TODO: needs storage and upload_to worked out
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

