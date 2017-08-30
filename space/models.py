import datetime
from django.db import models
from coredata.models import Unit
from autoslug import AutoSlugField
from courselib.slugs import make_slug
from coredata.models import CAMPUS_CHOICES, Person


BUILDING_CHOICES = (
    ('ASB', 'Applied Sciences Building'),
    ('TASC1', 'TASC 1'),
    ('SRY', 'Surrey'),
    ('SEE', 'SEE Building'),
    ('PTECH', 'Powertech'),
    ('BLARD', 'Ballard'),
    ('CC1', 'CC1'),
    ('NTECH', 'NEUROTECH'),
    ('SMH', 'SMH')
)

OWN_CHOICES = (
    ('OWN', 'SFU Owned'),
    ('LEASE', 'Leased')
)

INFRASTRUCTURE_CHOICES = (
    ('WET', 'Wet Lab'),
    ('DRY', 'Dry Lab'),
    ('HPC', 'High-Performance Computing'),
    ('STD', 'Standard')
)

CATEGORY_CHOICES = (
    ('STAFF', 'Staff'),
    ('FAC', 'Faculty'),
    ('PDOC', 'Post-Doc'),
    ('VISIT', 'Visitor'),
    ('SESS', 'Sessional'),
    ('LTERM', 'Limited-Term'),
    ('TA', 'TA'),
    ('GRAD', 'Grad Student'),
    ('URA', 'URA')
)


class RoomTypeManager(models.QuerySet):
    def visible(self, units):
        """
        Only see visible items, in this case also limited by accessible units.
        """
        return self.filter(hidden=False, unit__in=units)


class RoomType(models.Model):
    unit = models.ForeignKey(Unit, null=False)
    long_description = models.CharField(max_length=256, null=False, blank=False, help_text='e.g. "General Store"')
    code = models.CharField(max_length=50, null=False, blank=False, help_text='e.g. "STOR_GEN"')
    COU_code_description = models.CharField(max_length=256, null=False, blank=False, help_text='e.g. "Academic Office Support Space"')
    COU_code_value = models.DecimalField(max_digits=4, decimal_places=1, help_text='e.g. 10.1')
    hidden = models.BooleanField(default=False, null=False, blank=False, editable=False)

    objects = RoomTypeManager.as_manager()

    def autoslug(self):
        return make_slug(self.unit.slug + '-' + self.code + '-' + str(self.COU_code_value))

    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    def __unicode__(self):
        return u"%s-%s-%s-%s" % (self.unit.label, self.code, str(self.COU_code_value))


class LocationManager(models.QuerySet):
    def visible(self, units):
        """
        Only see visible items, in this case also limited by accessible units.
        """
        return self.filter(hidden=False, unit__in=units)


class Location(models.Model):
    unit = models.ForeignKey(Unit, null=False)
    campus = models.CharField(max_length=5, choices=CAMPUS_CHOICES, null=True, blank=True)
    building = models.CharField(max_length=5, choices=BUILDING_CHOICES, null=True, blank=True)
    floor = models.PositiveIntegerField(null=True, blank=True)
    room_number = models.CharField(max_length=25, null=True, blank=True)
    square_meters = models.DecimalField(max_digits=8, decimal_places=2)
    room_type = models.ForeignKey(RoomType, null=False)
    infrastructure = models.CharField(max_length=3, choices=INFRASTRUCTURE_CHOICES, null=True, blank=True)
    room_capacity = models.PositiveIntegerField(null=True, blank=True)
    category = models.CharField(max_length=5, choices=CATEGORY_CHOICES, null=True, blank=True)
    occupancy_count = models.PositiveIntegerField(null=True, blank=True)
    own_or_lease = models.CharField("SFU Owned or Leased", max_length=5, choices=OWN_CHOICES, null=True, blank=True)
    comments = models.CharField(max_length=400, null=True, blank=True)
    hidden = models.BooleanField(default=False, null=False, blank=False, editable=False)

    objects = LocationManager.as_manager()
    
    def autoslug(self):
        return make_slug(self.unit.slug + '-' + self.campus + '-' + self.building + '-' + str(self.floor) + '-' +
                         self.room_number)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    def __unicode__(self):
        return u"%s - %s - %s - %s - %s" % (self.unit.label, self.campus, self.building, str(self.floor),
                                            self.room_number)

    def get_current_booking(self):
        latest_booking = self.bookings.filter(start_date__lte=datetime.datetime.now(), hidden=False).\
            order_by('start_date').last()
        if latest_booking and (not latest_booking.end_date or latest_booking.end_date > datetime.datetime.now()):
            return latest_booking
        return None


class BookingRecordManager(models.QuerySet):
    def visible(self, units):
        """
        Only see visible items, in this case also limited by accessible units.
        """
        return self.filter(hidden=False, unit__in=units)


class BookingRecord(models.QuerySet):
    location = models.ForeignKey(Location, related_name='bookings')
    person = models.ForeignKey(Person)
    start_time = models.DateTimeField(default=datetime.datetime.now())
    end_time = models.DateTimeField(null=True, blank=True)
    hidden = models.BooleanField(default=False, null=False, blank=False, editable=False)

    objects = BookingRecordManager.as_manager()

    def autoslug(self):
        return make_slug(self.location.slug + '-' + self.person.userid + '-' +
                         str(self.start_time.date()))

    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

