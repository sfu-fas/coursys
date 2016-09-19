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


    def past(self, units):
        return self.visible(units).filter(end_date__lt=timezone_today())


    def current(self, units):
        return self.visible(units).filter(Q(start_date__gte=timezone_today()) | Q(end_date__gte=timezone_today()))


class OutreachEvent(models.Model):
    """
    An outreach event.  These are different than our other events, as they are to be attended by non-users of the
    system.
    """
    title = models.CharField(max_length=60, null=False, blank=False)
    start_date = models.DateTimeField('Start Date and Time', default=timezone_today,
                                      help_text='Event start date and time.  Use 24h format for the time if needed.')
    end_date = models.DateTimeField('End Date and Time', blank=False, null=False,
                                    help_text='Event end date and time')
    location = models.CharField(max_length=400, blank=True, null=True)
    description = models.CharField(max_length=800, blank=True, null=True)
    score = models.DecimalField(max_digits=2, decimal_places=0, max_length=2, null=True, blank=True,
                                help_text='The score according to the event score matrix')
    unit = models.ForeignKey(Unit, blank=False, null=False)
    resources = models.CharField(max_length=400, blank=True, null=True, help_text="Resources needed for this event.")
    cost = models.DecimalField(blank=True, null=True, max_digits=8, decimal_places=2, help_text="Cost of this event")
    hidden = models.BooleanField(default=False, null=False, blank=False, editable=False)
    notes = models.CharField(max_length=400, blank=True, null=True, help_text='Special notes to registrants.  These '
                                                                              '*will* be displayed on the registration '
                                                                              'forms.')
    email = models.EmailField('Contact e-mail', null=True, blank=True,
                              help_text='Contact email.  Address that will be given to registrants on the registration '
                                        'success page in case they have any questions/problems.')
    closed = models.BooleanField('Close Registration', default=False,
                                 help_text='If this box is checked, people will not be able to register for this '
                                           'event even if it is still current.')
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

    # TODO add copy method to copy from one event to another

    def registration_count(self):
        return OutreachEventRegistration.objects.attended_event(self).count()


class OutreachEventRegistrationQuerySet(models.QuerySet):
    """
    As usual, define some querysets.
    """
    def visible(self, units):
        """
        Only see visible items, in this case also limited by accessible units.
        """
        return self.filter(hidden=False, event__unit__in=units)

    def current(self, units):
        """
        Return visible registrations for current events
        """
        return self.visible(units).filter(event__in=OutreachEvent.objects.current(units))

    def past(self, units):
        """
        Return visible registrations for past events
        """
        return self.visible(units).filter(event__in=OutreachEvent.objects.past(units))

    def attended_event(self, event):
        return self.filter(hidden=False, event=event, attended=True)

    def by_event(self, event):
        return self.filter(hidden=False, event=event)


class OutreachEventRegistration(models.Model):
    """
    An event registration.  Only outreach admins should ever need to see this.  Ideally, the users (not loggedin)
    should only ever have to fill in these once, but we'll add a UUID in case we need to send them back to them.
    """
    # Don't make the UUID the primary key.  We need a primary key that can be cast to an int for our logger.
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, null=False)
    last_name = models.CharField("Participant Last Name", max_length=32)
    first_name = models.CharField("Participant First Name", max_length=32)
    middle_name = models.CharField("Participant Middle Name", max_length=32, null=True, blank=True)
    age = models.DecimalField("Participant Age", null=True, blank=True, max_digits=2, decimal_places=0)
    parent_name = models.CharField(max_length=100, blank=False, null=False)
    parent_phone = models.CharField(max_length=15, blank=False, null=False)
    email = models.EmailField("Contact E-mail")
    event = models.ForeignKey(OutreachEvent, blank=False, null=False)
    waiver = models.BooleanField(default=False)
    previously_attended = models.BooleanField("I have previously attended this event", default=False,
                                              help_text='Check here if you have attended this event in the past')
    school = models.CharField("Participant School", null=True, blank=True, max_length=200)
    grade = models.PositiveSmallIntegerField("Participant Grade", blank=False, null=False)
    hidden = models.BooleanField(default=False, null=False, blank=False, editable=False)
    notes = models.CharField("Allergies/Dietary Restrictions", max_length=400, blank=True, null=True)
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
        return u"%s, %s %s" % (self.last_name, self.first_name, self.middle_name or '')

    def save(self, *args, **kwargs):
        self.last_modified = timezone.now()
        super(OutreachEventRegistration, self).save(*args, **kwargs)

