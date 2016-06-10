"""
A module written to manage our outreach events.
"""

from django.db import models
from django.utils import timezone
from django.db.models import Q
from coredata.models import Unit
import uuid
from autoslug import AutoSlugField
from courselib.slugs import make_slug


def timezone_today():
    """
    Return the timezone-aware version of datetime.date.today()
    """
    # field default must be a callable (so it's the "today" of the request, not the "today" of the server startup)
    return timezone.now()


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

    """
    A current event may have already started
    """
    def current(self, units):
        return self.visible(units).filter(Q(start_date__gte=timezone_today()) | Q(end_date__gte=timezone_today()))


class OutreachEvent(models.Model):
    """
    An outreach event.  These are different than our other events, as they are to be attended by non-users of the
    system.
    """
    title = models.CharField(max_length=60, null=False, blank=False)
    start_date = models.DateTimeField('Start Date and Time', default=timezone_today, help_text='Event start date and time.  Use 24h format for the time if needed.')
    end_date = models.DateTimeField('End Date and Time', blank=True, null=True, help_text='Event end date and time, if any')
    description = models.CharField(max_length=400, blank=True, null=True)
    score = models.DecimalField(max_digits=2, decimal_places=0, max_length=2, null=True, blank=True)
    unit = models.ForeignKey(Unit, blank=False, null=False)
    resources = models.CharField(max_length=400, blank=True, null=True, help_text="Resources needed for this event.")
    cost = models.DecimalField(blank=True, null=True, max_digits=8, decimal_places=2, help_text="Cost of this event")
    hidden = models.BooleanField(default=False, null=False, blank=False, editable=False)
    objects = EventQuerySet.as_manager()

    def autoslug(self):
        return make_slug(self.unit.slug + '-' + self.title + '-' + str(self.start_date.date()))

    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    def __unicode__(self):
        return u"%s - %s - %s" % (self.title, self.unit.label, self.start_date)

    def delete(self):
        """Like most of our objects, we don't want to ever really delete it."""
        self.hidden = True
        self.save()

    def current(self):
        """
        Find out if an event is still current.  Otherwise, we shouldn't be able to register for it.
        """
        return self.start_date > timezone_today() or self.end_date >= timezone_today()


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
    last_name = models.CharField("Participant Last Name", max_length=32)
    first_name = models.CharField("Participant First Name", max_length=32)
    middle_name = models.CharField("Participant Middle Name", max_length=32, null=True, blank=True)
    age = models.DecimalField("Participant Age", null=True, blank=True, max_digits=2, decimal_places=0)
    contact = models.CharField("Emergency Contact", max_length=400, blank=True, null=True)
    email = models.EmailField("Contact E-mail")
    event = models.ForeignKey(OutreachEvent, blank=False, null=False)
    waiver = models.BooleanField(default=False, help_text="I agree to have <insert legalese here>")
    school = models.CharField("Participant School", null=True, blank=True, max_length=200)
    hidden = models.BooleanField(default=False, null=False, blank=False, editable=False)
    notes = models.CharField("Special Instructions", max_length=400, blank=True, null=True)
    objects = OutreachEventRegistrationQuerySet.as_manager()
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    last_modified = models.DateTimeField(editable=False, blank=False, null=False)
    attended = models.BooleanField(default=True, editable=False, blank=False, null=False)

    def __unicode__(self):
        return u"%s, %s = %s" % (self.last_name, self.first_name, self.event)

    def delete(self):
        """Like most of our objects, we don't want to ever really delete it."""
        self.hidden = True
        self.save()

    def fullname(self):
        return u"%s, %s %s" % (self.last_name, self,first_name, self.middle_name or '')

    def save(self, *args, **kwargs):
        self.last_modified = timezone.now()
        super(OutreachEventRegistration, self).save(*args, **kwargs)
