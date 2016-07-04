import os
import datetime

from autoslug import AutoSlugField
from django.db import models

from django.conf import settings
from django.core.files.storage import FileSystemStorage

from coredata.models import VISA_STATUSES as REAL_VISA_STATUSES, Person
from django.utils import timezone
from courselib.json_fields import JSONField
from coredata.models import Semester
from django.db.models.query import QuerySet

# "citizen" isn't truly a visa status, but it's something we want to track here.
# SIMS has no Work Visa status, so we're adding that here too.
VISA_STATUSES = (('Citizen', 'Citizen'), ('Work', 'Work Visa')) + REAL_VISA_STATUSES

EXPIRY_STATUSES = ['Expired', 'Expiring Soon', 'Valid']

NoteSystemStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)

def timezone_today():
    """
    Return the timezone-aware version of datetime.date.today()
    """
    # field default must be a callable (so it's the "today" of the request, not the "today" of the server startup)
    return timezone.now().date()


class VisaManager(models.Manager):
    def visible(self):
        qs = self.get_queryset()
        return qs.filter(hidden=False)

    def visible_given_user(self, person):
        qs = self.get_queryset()
        return qs.filter(hidden=False, person=person)


class Visa (models.Model):
    person = models.ForeignKey(Person, null=False, blank=False)
    status = models.CharField(max_length=50, choices=VISA_STATUSES, default='')
    start_date = models.DateField('Start Date', default=timezone_today, help_text='First day of visa validity')
    end_date = models.DateField('End Date', blank=True, null=True, help_text='Expiry of the visa (if known)')
    config = JSONField(null=False, blank=False, editable=False, default=dict)  # For future fields
    hidden = models.BooleanField(default=False, editable=False)

    objects = VisaManager()

    class Meta:
        ordering = ('start_date',)

    # Helper methods to display a proper status we can sort on
    def is_valid(self):
        return self.start_date <= timezone_today() and (self.end_date is not None and timezone_today() < self.end_date)

    def is_expired(self):
        return self.end_date is not None and timezone_today() > self.end_date

    # If this visa will expire before the end of next semester, that may be important
    # We are checking the next semester because TA/RA contracts are usually drawn up
    # near the end of a semester for the next semester.
    def is_almost_expired(self):
        next_semester = Semester.next_starting()
        return (self.is_valid()) and (self.end_date is not None and self.end_date < next_semester.end)

    def get_validity(self):
        if self.is_expired():
            return EXPIRY_STATUSES[0]
        if self.is_almost_expired():
            return EXPIRY_STATUSES[1]
        if self.is_valid():
            return EXPIRY_STATUSES[2]
        return "Unknown"  # We'll hit this if the end_date is null.

    def __unicode__(self):
        return u"%s, %s, %s" % (self.person, self.status, self.start_date)

    def hide(self):
        self.hidden = True

    def has_attachments(self):
        return VisaDocumentAttachment.objects.filter(visa=self, hidden=False).count() > 0

    @staticmethod
    def import_for(people):
        """
        Get visa status for these people from SIMS
        """
        from grad.importer.queries import grad_metadata, metadata_translation_tables

        _, countries, visas = metadata_translation_tables()
        data = grad_metadata([p.emplid for p in people])
        for d in data:
            emplid = d[1]
            country = d[4]
            visatype = d[5]
            if country == 'CAN':
                # Canadian citizen and be done with it.
                print emplid, 'Citizen'
            elif visatype:
                print emplid, visas.get(visatype, None)

    @staticmethod
    def get_visas(people):
        """
        Returns all visible visas for given people

        :param Person people: The people we are querying for visa information
        :type: list of Person
        :return: A list of visas
        :rtype: list
        """
        return Visa.objects.visible().filter(person__in=people).order_by('start_date')


def visa_attachment_upload_to(instance, filename):
    """
    callback to avoid path in the filename(that we have append folder structure to) being striped
    """
    fullpath = os.path.join(
        'visas',
        instance.visa.person.userid_or_emplid(),
        str(instance.visa.id),
        datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
        filename.encode('ascii', 'ignore'))
    return fullpath


class VisaDocumentAttachmentManager(models.Manager):
    def visible(self):
        qs = self.get_queryset()
        return qs.filter(hidden=False)


class VisaDocumentAttachment(models.Model):
    """
    Document attached to a CareerEvent.
    """
    visa = models.ForeignKey(Visa, null=False, blank=False, related_name="attachments")
    title = models.CharField(max_length=250, null=False)
    slug = AutoSlugField(populate_from='title', null=False, editable=False, unique_with=('visa',))
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, help_text='Document attachment created by.')
    contents = models.FileField(storage=NoteSystemStorage, upload_to=visa_attachment_upload_to, max_length=500)
    mediatype = models.CharField(max_length=200, null=True, blank=True, editable=False)
    hidden = models.BooleanField(default=False, editable=False)

    objects = VisaDocumentAttachmentManager()

    def __unicode__(self):
        return self.contents.name

    class Meta:
        ordering = ("created_at",)
        unique_together = (("visa", "slug"),)

    def contents_filename(self):
        return os.path.basename(self.contents.name)

    def hide(self):
        self.hidden = True
        self.save()
