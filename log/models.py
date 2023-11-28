import copy
import datetime
import uuid
from typing import Any, Dict, Tuple, List

from django.db import models, connection
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


PURGE_AFTER_DAYS = 30


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


def data_property(field, default=None):
    def getter(self):
        return self.data[field] if field in self.data else copy.copy(default)

    def setter(self, val):
        self.data[field] = val

    return property(getter, setter)


class EventLogQuerySet(models.QuerySet):
    def data_contains(self, data: Dict[str, Any]):
        if connection.features.supports_json_field_contains:
            return self.filter(data__contains=data)
        else:
            # fake it in sqlite for dev: iterate the queryset to manually find matches
            pks = set()

            for o in self:
                for k, v in data.items():
                    if not (k in o.data and o.data[k] == v):
                        break
                else:
                    pks.add(o.pk)

            return self.filter(pk__in=pks)

    def to_polars(self, schema: List[Tuple[str, type]]) -> 'pl.LazyFrame':
        import polars as pl
        columns = [pr[0] for pr in schema]
        data = [tuple(getattr(o, c) for c in columns) for o in self]
        return pl.LazyFrame(data=data, schema=schema, orient='row')


class EventLogManager(models.Manager):
    def get_queryset(self):
        return EventLogQuerySet(self.model, using=self._db)


class EventLogEntry(models.Model):
    """
    Abstract base class for logging system events.

    Logic of the database field vs JSON data split:
    * real field: efficient querying and sorting. Use for things that and likely to be searched and/or always there.
    * JSON data: flexible. Use for everything else.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid1, editable=False)
    time = models.DateTimeField(blank=False, null=False, help_text='Time of the *start* of this event.')
    duration = models.DurationField(blank=False, null=False, help_text='Time taken for this event.')
    data = models.JSONField()

    objects = EventLogManager()

    class Meta:
        abstract = True
        ordering = ['-time']

    def __str__(self):
        return f'EventLogEntry@{self.time.isoformat()}'

    @staticmethod
    def purge_old_logs(days=PURGE_AFTER_DAYS):
        for cls in EVENT_LOG_TYPES.values():
            cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
            cls.objects.filter(time__lt=cutoff).delete()


class RequestLog(EventLogEntry):
    """
    Log of an HTTP request (which was handled by Django: non-static response).

    Created by courselib.middleware.LoggingMiddleware
    """
    username = models.CharField(max_length=32, null=True, db_index=True)
    method = models.CharField(max_length=10, null=False)
    path = models.CharField(max_length=1024, null=False)
    ip = data_property('ip')
    user_agent = data_property('user_agent')
    session_key = data_property('session_key')
    view_name = data_property('view_name')
    status_code = data_property('status_code')

    display_columns = ['time', 'duration', 'username', 'method', 'path', 'status_code']
    table_column_config = [None, None, None, None, None, {'orderable': False}]

    @classmethod
    def ip_address_report(cls) -> 'pl.LazyFrame':
        import polars as pl
        cutoff = datetime.datetime.now() - datetime.timedelta(days=7)
        qs = cls.objects.filter(time__gte=cutoff)
        schema = [('ip', str), ('method', str)]
        df = qs.to_polars(schema)
        return df.group_by('ip').agg(pl.count('*')).rename({'method': 'count'}).sort('count', descending=True)


class CeleryTaskLog(EventLogEntry):
    """
    Log of a Celery task.

    Created by courselib.celerytasks.task
    """
    task = models.CharField(max_length=255, null=False, db_index=True)
    queue = data_property('queue')

    display_columns = ['time', 'duration', 'task']
    table_column_config = [None, None, None]


# dict of EventLogEntry for discovery in log exploration UI
EVENT_LOG_TYPES = {
    'request': RequestLog,
    'task': CeleryTaskLog,
}
