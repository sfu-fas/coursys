from django.db import models
from coredata.models import VISA_STATUSES, Person
from django.utils import timezone
from courselib.json_fields import JSONField
from coredata.models import Semester
from django.db.models.query import QuerySet
from model_utils.managers import PassThroughManager

EXPIRY_STATUSES = ['Expired', 'Expiring Soon', 'Valid']

def timezone_today():
    """
    Return the timezone-aware version of datetime.date.today()
    """
    # field default must be a callable (so it's the "today" of the request, not the "today" of the server startup)
    return timezone.now().date()


class VisaQuerySet(QuerySet):

        def visible(self):
            return self.filter(hidden=False)


class Visa (models.Model):
    person = models.ForeignKey(Person, null=False, blank=False)
    status = models.CharField(max_length=50, choices=VISA_STATUSES, default='')
    start_date = models.DateField('Start Date', default=timezone_today)
    end_date = models.DateField('End Date', blank=True, null=True)
    config = JSONField(null=False, blank=False, editable=False, default=dict)  # For future fields
    hidden = models.BooleanField(default=False, editable=False)

    objects = PassThroughManager.for_queryset_class(VisaQuerySet)()

    class Meta:
        ordering = ('start_date',)

    # Helper methods to display a proper status we can sort on
    def is_valid(self):
        return self.start_date <= timezone_today() and (self.end_date is not None and timezone_today() < self.end_date)

    def is_expired(self):
        return self.end_date is not None and timezone_today() > self.end_date

    # If this visa will expire this semester, that may be important
    # A better business rule may be forthcoming.
    def is_almost_expired(self):
        current = Semester.current()
        return (self.is_valid()) and (self.end_date is not None and self.end_date < current.end)

    def get_validity(self):
        if self.is_expired():
            return EXPIRY_STATUSES[0]
        if self.is_almost_expired():
            return EXPIRY_STATUSES[1]
        if self.is_valid():
            return EXPIRY_STATUSES[2]
        return "Unknown"  # We'll hit this if the end_date is null.

    def __unicode__(self):
        return "%s, %s, %s" % (self.person, self.status, self.start_date)

    def hide(self):
        self.hidden = True

