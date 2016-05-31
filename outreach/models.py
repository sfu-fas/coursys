"""
A module written to manage our outreach events.
"""

from django.db import models
from django.utils import timezone
from coredata.models import Unit
import uuid
from autoslug import AutoSlugField
from courselib.slugs import make_slug


def timezone_today():
    """
    Return the timezone-aware version of datetime.date.today()
    """
    # field default must be a callable (so it's the "today" of the request, not the "today" of the server startup)
    return timezone.now().date()


class EventQuerySet(models.QuerySet):
    """
    As usual, define some querysets.
    """
    def visible(self, units):
        """
        Only see visible items, in this case also limited by accessible units.
        """
        return self.filter(hidden=False, unit__in=units)

    def upcoming(self, units):
        return self.visible(units).filter(start_date__gte=timezone_today())

    def past(self, units):
        return self.visible(units).filter(end_date__lte=timezone_today())


class OutreachEvent(models.Model):
    """
    An outreach event.  These are different than our other events, as they are to be attended by non-users of the
    system.
    """
    title = models.CharField(max_length=60, null=False, blank=False)
    start_date = models.DateField('Start Date', default=timezone_today, help_text='Event start date')
    end_date = models.DateField('End Date', blank=True, null=True, help_text='Event end date, if any')
    description = models.CharField(max_length=400, blank=True, null=True)
    unit = models.ForeignKey(Unit, blank=False, null=False)
    hidden = models.BooleanField(default=False, null=False, blank=False, editable=False)
    objects = EventQuerySet.as_manager()

    def __unicode__(self):
        return u"%s - %s - %s" % (self.title, self.unit.label, self.start_date)

    def delete(self):
        """Like most of our objects, we don't want to ever really delete it."""
        self.hidden = True
        self.save()

class OutreachEventRegistrationQuerySet(models.QuerySet):
    """
    As usual, define some querysets.
    """
    def visible(self, units):
        """
        Only see visible items, in this case also limited by accessible units.
        """
        return self.filter(hidden=False, unit__in=units)


class OutreachEventRegistration(models.Model):
    """
    An event registration.  Only outreach admins should ever need to see this.  Ideally, the users (not loggedin)
    should only ever have to fill in these once, but we'll add a UUID in case we need to send them back to them.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    last_name = models.CharField(max_length=32)
    first_name = models.CharField(max_length=32)
    middle_name = models.CharField(max_length=32, null=True, blank=True)
    email = models.EmailField()
    event = models.ForeignKey(OutreachEvent, blank=False, null=False)
    waiver = models.BooleanField(default=False, help_text="I agree to have <insert legalese here>")
    hidden = models.BooleanField(default=False, null=False, blank=False, editable=False)
    objects = OutreachEventRegistrationQuerySet.as_manager()


    def __unicode__(self):
        return u"%s, %s = %s" % (self.last_name, self.first_name, self.event)

    def delete(self):
        """Like most of our objects, we don't want to ever really delete it."""
        self.hidden = True
        self.save()
