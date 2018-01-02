from django.utils import timezone
from django.db import models
from django.template.loader import get_template
from django.template import Context
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from coredata.models import Unit, JSONField, config_property
from autoslug import AutoSlugField
from courselib.slugs import make_slug
from coredata.models import CAMPUS_CHOICES, Person
from courselib.storage import UploadedFileStorage, upload_path
from courselib.branding import product_name
import os


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


def timezone_today():
    """
    Return the timezone-aware version of datetime.date.today()
    """
    # field default must be a callable (so it's the "today" of the request, not the "today" of the server startup)
    return timezone.now()


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
    COU_code_description = models.CharField(max_length=256, null=False, blank=False,
                                            help_text='e.g. "Academic Office Support Space"')
    space_factor = models.DecimalField(max_digits=3, decimal_places=1, blank=True, default=0.0)
    COU_code_value = models.DecimalField(max_digits=4, decimal_places=1, help_text='e.g. 10.1', blank=True, null=True)
    hidden = models.BooleanField(default=False, null=False, blank=False, editable=False)
    config = JSONField(null=False, blank=False, editable=False, default=dict)

    objects = RoomTypeManager.as_manager()

    def autoslug(self):
        return make_slug(self.unit.slug + '-' + self.code + '-' + str(self.COU_code_value))

    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    def __unicode__(self):
        return u"%s-%s-%s" % (self.unit.label, self.code, str(self.COU_code_value))


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
    floor = models.PositiveIntegerField(null=False, blank=False)
    room_number = models.CharField(max_length=25, null=False, blank=False)
    square_meters = models.DecimalField(max_digits=8, decimal_places=2)
    room_type = models.ForeignKey(RoomType, null=False)
    infrastructure = models.CharField(max_length=3, choices=INFRASTRUCTURE_CHOICES, null=True, blank=True)
    room_capacity = models.PositiveIntegerField(null=True, blank=True)
    category = models.CharField(max_length=5, choices=CATEGORY_CHOICES, null=True, blank=True)
    occupancy_count = models.PositiveIntegerField(null=True, blank=True)
    own_or_lease = models.CharField("SFU Owned or Leased", max_length=5, choices=OWN_CHOICES, null=True, blank=True)
    comments = models.CharField(max_length=400, null=True, blank=True)
    hidden = models.BooleanField(default=False, null=False, blank=False, editable=False)
    config = JSONField(null=False, blank=False, editable=False, default=dict)

    objects = LocationManager.as_manager()

    def autoslug(self):
        return make_slug(self.unit.slug + '-' + self.campus + '-' + self.building + '-' + str(self.floor) + '-' +
                         self.room_number)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    def __unicode__(self):
        return u"%s - %s - %s - %s - %s" % (self.unit.label, self.campus, self.building, str(self.floor),
                                            self.room_number)

    def get_current_booking(self):
        latest_booking = self.bookings.visible().filter(start_time__lte=timezone_today()).order_by('start_time').last()
        if latest_booking and (not latest_booking.end_time or latest_booking.end_time > timezone_today()):
            return latest_booking
        return None

    def has_bookings(self):
        return self.bookings.filter(hidden=False).count() > 0

    def get_bookings(self):
        return self.bookings.filter(hidden=False)

    def mark_conflicts(self):
        # A stupid nested loop to see if there are any conflicts within the bookings for this location
        self.conflicts = False
        for a in self.get_bookings():
            a.conflict = False
            for b in self.get_bookings().exclude(id=a.id):
                if a.end_time is None and b.end_time is None:
                    a.conflict = True
                    break
                if a.end_time is None and a.start_time < b.end_time:
                    a.conflict = True
                    break
                if b.end_time is None and ((a.start_time > b.start_time) or (a.end_time > b.start_time)):
                    a.conflict = True
                    break
                if a.end_time is not None and b.end_time is not None and a.start_time < b.end_time \
                        and a.end_time > b.start_time:
                    a.conflict = True
            a.save()


class BookingRecordManager(models.QuerySet):
    def visible(self):
        """
        Only see visible items, in this case also limited by accessible units.
        """
        return self.filter(hidden=False)


class BookingRecord(models.Model):
    location = models.ForeignKey(Location, related_name='bookings')
    person = models.ForeignKey(Person, related_name='+')
    start_time = models.DateTimeField(default=timezone_today)
    end_time = models.DateTimeField(null=True, blank=True)
    form_submission_URL = models.CharField(null=True, blank=True, max_length=1000,
                                           help_text="If the user filled in a form to get this booking created, put "
                                                     "its URL here.")
    notes = models.CharField(null=True, blank=True, max_length=1000)
    hidden = models.BooleanField(default=False, null=False, blank=False, editable=False)
    config = JSONField(null=False, blank=False, editable=False, default=dict)
    last_modified = models.DateTimeField(blank=False, null=False, editable=False)
    last_modified_by = models.ForeignKey(Person, null=True, blank=True, editable=False, related_name='+')

    objects = BookingRecordManager.as_manager()

    # A property to mark if this booking conflicts with any others.
    conflict = config_property('conflict', False)

    def autoslug(self):
        return make_slug(self.location.slug + '-' + self.person.userid + '-' +
                         str(self.start_time.date()))

    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    def __unicode__(self):
        return u"%s - %s" % (self.person.name(), self.start_time)

    def save(self, editor=None, *args, **kwargs):
        # Only note the last modified things if we have an editor.  Otherwise, the object is being changed
        # by the conflict checking code or the code end-dating it automagically.
        if editor:
            self.last_modified = timezone_today()
            self.last_modified_by = editor
        # In remote cases, we could have created the object without an editor automagically, like when creating
        # the fixtures.  In that case, only if we don't have a previous last_modified, create it.
        elif not self.last_modified:
            self.last_modified = timezone_today()
        super(BookingRecord, self).save(*args, **kwargs)
        self.end_date_others()

    # If we have other bookings without and end-date, apply the new one's start date as the end-date.
    def end_date_others(self):
        for b in BookingRecord.objects.visible().filter(location=self.location, end_time__isnull=True,
                                                        start_time__lt=self.start_time).exclude(id=self.id):
            b.end_time = self.start_time
            b.save()

    def has_attachments(self):
        return self.attachments.visible().count() > 0

    def get_attachments(self):
        return self.attachments.visible().order_by('created_at')

    def has_memos(self):
        return self.memos.count() > 0

    def get_memos(self):
        return self.memos.objects.all().order_by('created_at')

def space_attachment_upload_to(instance, filename):
    return upload_path('space', str(instance.booking_record.start_time.year), filename)


class BookingRecordAttachmentQueryset(models.QuerySet):
    def visible(self):
        return self.filter(hidden=False)


class BookingRecordAttachment(models.Model):
    booking_record = models.ForeignKey(BookingRecord, related_name='attachments')
    title = models.CharField(max_length=250, null=False)
    slug = AutoSlugField(populate_from='title', null=False, editable=False, unique_with=('booking_record',))
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person)
    contents = models.FileField(storage=UploadedFileStorage, upload_to=space_attachment_upload_to, max_length=500)
    mediatype = models.CharField(max_length=200, null=True, blank=True, editable=False)
    hidden = models.BooleanField(default=False, editable=False)

    objects = BookingRecordAttachmentQueryset.as_manager()

    def __unicode__(self):
        return self.contents.name

    class Meta:
        ordering = ("created_at",)
        unique_together = (("booking_record", "slug"),)

    def contents_filename(self):
        return os.path.basename(self.contents.name)

    def hide(self):
        self.hidden = True
        self.save()


class BookingMemo(models.Model):
    booking_record = models.ForeignKey(BookingRecord, related_name='memos')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person)

    def email_memo(self):
        """
        Emails the person to whom the booking is assigned.
        """
        subject = 'Booking notification'
        from_email = settings.DEFAULT_FROM_EMAIL
        template = get_template('space/emails/memo.txt')
        context = Context({'booking': self.booking_record, 'CourSys': product_name(hint='admin')})
        msg = EmailMultiAlternatives(subject, template.render(context), from_email,
                                     [self.booking_record.person.email()], headers={'X-coursys-topic': 'space'})
        msg.send()
