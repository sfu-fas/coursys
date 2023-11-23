import copy
import uuid
from sqlite3 import NotSupportedError
from typing import Any

import django.db.utils
from django.db import models, connection
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class LogEntry(models.Model):
    """
    A record of activity within the system.  The "description" should be a reasonably-complete
    description of the activity that has occurred.  The "related_object" should be the object
    that was modified.
    
    self.userid == '' indicated action by non-logged-in user.
    
    Sample usage (e.g. editing a student's grade on an assignment)
        activity = NumericActivity.objects.get(...)
        student = Person.objects.get(...)
        grade = NumericGrade.objects.get(...)
        grade.value = new_grade
        grade.save()
        l = LogEntry(userid=request.user.username, 
              description="edited grade on %s for %s changed to %s" % (activity, student.userid, new_grade),
              related_object=grade )
        l.save()
    """
    userid = models.CharField(max_length=8, null=False, db_index=True,
        help_text='Userid who made the change')
    datetime = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255, help_text="Description from the system of the change made")
    comment = models.TextField(null=True, help_text="Comment from the user (if available)")

    # link to object that was changed
    content_type = models.ForeignKey(ContentType, null=True, related_name="content_type", on_delete=models.SET_NULL)
    object_id = models.PositiveIntegerField(null=True)
    related_object = GenericForeignKey('content_type', 'object_id')
    class Meta:
        ordering = ['-datetime']

    def save(self, *args, **kwargs):
        # self.content_type might be null if the related item is deleted, but must be created with one.
        assert self.content_type
        if len(self.description) > 255:
            self.description = self.description[:252] + '...'
        return super().save(*args, **kwargs)

    def display(self):
        return "%s - %s - %s" % (self.userid, self.description, self.comment)

    __str__ = display


class EventLogManager(models.Manager):
    def data_contains(self, data: dict[str, Any]):
        if connection.features.supports_json_field_contains:
            return self.get_queryset().filter(data__contains=data)
        else:
            # fake it in sqlite for dev
            qs = self.get_queryset()
            for o in qs:
                for k,v in data.items():
                    if not (k in o.data and o.data[k] == v):
                        break
                else:
                    yield o


def data_property(field, default=None):
    def getter(self):
        return self.data[field] if field in self.data else copy.copy(default)

    def setter(self, val):
        self.data[field] = val

    return property(getter, setter)


class EventLogEntry(models.Model):
    """
    Abstract base class for logging system events.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid1, editable=False)
    time = models.DateTimeField(blank=False, null=False, help_text='Time of the *start* of this event.')
    duration = models.DurationField(blank=False, null=False)
    username = models.CharField(max_length=32, null=True, db_index=True)
    data = models.JSONField()

    objects = EventLogManager()

    class Meta:
        abstract = True
        ordering = ['-time']

    def __str__(self):
        return f'EventLogEntry@{self.time.isoformat()}'

    path = data_property('path')


class RequestLog(EventLogEntry):
    """
    Log of an HTTP request (handled by Django: non-static file).
    """
    display_columns = ['time', 'path', 'user', 'status_code']
    table_column_config = [None, {'orderable': False}, {'orderable': False}, {'orderable': False}]


class CeleryTaskLog(EventLogEntry):
    """
    Log of a Celery task
    """
    pass


# dict of EventLogEntry for discovery in log exploration UI
EVENT_LOG_TYPES = {
    'request': RequestLog,
    'task': CeleryTaskLog,
}
