from __future__ import unicode_literals

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
EVENT_CHOICES = [(key, cls.name) for key, cls in EVENT_HANDLERS.items()]


class IgnoreDeleted(models.Manager):
    def get_queryset(self):
        return super(IgnoreDeleted, self).get_queryset().filter(deleted=False)


class Contact(models.Model):
    unit = models.ForeignKey(Unit, null=False, blank=False)
    slug = AutoSlugField(populate_from='slug_string', unique_with=('unit',),
                         slugify=make_slug, null=False, editable=False)
    last_name = models.CharField(max_length=32)
    first_name = models.CharField(max_length=32)
    middle_name = models.CharField(max_length=32, null=True, blank=True)
    pref_first_name = models.CharField("Preferred First Name", max_length=32, null=True, blank=True)
    title = models.CharField(max_length=4, null=True, blank=True)
    email = models.EmailField(blank=True, null=True)
    phone = models.Charfield(max_length=15, null=True, blank=True)
    deleted = models.BooleanField(default=False)
    config = JSONField(default=dict)

    objects = IgnoreDeleted()

    @property
    def slug_string(self):
        return u'%s %s' % (self.first_name, self.last_name)


class Event(models.Model):
    contact = models.ForeignKey(Contact, null=False, blank=False)
    event_type = models.CharField(max_length=10, choices=EVENT_CHOICES)
    slug = AutoSlugField(populate_from='slug_string', unique_with=('contact',),
                         slugify=make_slug, null=False, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    attachment = models.FileField(null=True, max_length=500) # TODO: needs storage and upload_to worked out
    deleted = models.BooleanField(default=False)
    config = JSONField(default=dict)

    objects = IgnoreDeleted()

    @property
    def slug_string(self):
        return u'%s-%s' % (self.timestamp.year, self.event_type)

    @property
    def handler_class(self):
        return EVENT_HANDLERS[self.event_type]