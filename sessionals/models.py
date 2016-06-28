"""
A module written to manage our sessional contracts.  This will be similar to RA and TA contracts, but with
some important differences.
"""

from django.db import models
from autoslug import AutoSlugField
from coredata.models import AnyPerson, Unit, JSONField, CourseOffering
from courselib.slugs import make_slug


# TODO:  A SemesterConfig object to store default appointment start/end and pay start/end dates per semester.  All
# schools use the same dates, and they should never change, as per the latest meetings, so let them manage them to
# pre-populate the contracts when they are being created.


class SessionalAccountQuerySet(models.QuerySet):
    """
    As usual, define some querysets.
    """
    def visible(self, units):
        """
        Only see visible items, in this case also limited by accessible units.
        """
        return self.filter(hidden=False, unit__in=units)


class SessionalAccount(models.Model):
    """
    Sessionals have their own position and account number per unit.  Each unit has up to
    two of these account/position numbers, one for SFUFA and one for TSSU.  They don't need
    to fill in two things for every contract, so we'll store them together and let them pick.
    """
    unit = models.ForeignKey(Unit, null=False, blank=False)
    title = models.CharField(max_length=60)
    account_number = models.PositiveIntegerField(null=False, blank=False)
    position_number = models.PositiveIntegerField(null=False, blank=False)

    def autoslug(self):
        """As usual, create a unique slug for each object"""
        return make_slug(self.unit.label + '-' + unicode(self.account_number) + '-' + unicode(self.title))

    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)
    hidden = models.BooleanField(null=False, default=False, editable=False)
    objects = SessionalAccountQuerySet.as_manager()

    def __unicode__(self):
        return u"%s - %s" % (self.unit, self.title)

    def delete(self):
        """Like most of our objects, we don't want to ever really delete it."""
        self.hidden = True
        self.save()


class SessionalContractQuerySet(models.QuerySet):
    """
    As usual, define some querysets.
    """
    def visible(self, units):
        """
        Only see visible items, in this case also limited by accessible units.
        """
        return self.filter(hidden=False, unit__in=units)


class SessionalContract(models.Model):
    """
    Similar to TA or RA contract, but we need to be able to use them with people who aren't in the
    system yet.
    """
    sessional = models.ForeignKey(AnyPerson, null=False, blank=False)
    account = models.ForeignKey(SessionalAccount, null=False, blank=False)
    unit = models.ForeignKey(Unit, null=False, blank=False)
    appointment_start = models.DateField(null=True, blank=True)
    appointment_end = models.DateField(null=True, blank=True)
    pay_start = models.DateField()
    pay_end = models.DateField()
    # Was going to add a Semester, but since the offering itself has a semester, no need for it.
    offering = models.ForeignKey(CourseOffering, null=False, blank=False)

    created = models.DateTimeField(auto_now_add=True, editable=False)
    created_by = models.CharField(max_length=20, null=False, blank=False, editable=False)
    hidden = models.BooleanField(null=False, default=False, editable=False)
    config = JSONField(null=False, blank=False, editable=False, default=dict)
    objects = SessionalContractQuerySet.as_manager()

    def autoslug(self):
        """As usual, create a unique slug for each object"""
        return make_slug(self.sessional + "-" + self.offering)

    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    def __unicode__(self):
        return u"%s - %s" % (self.sessional, self.unit)

    def delete(self):
        """Like most of our objects, we don't want to ever really delete it."""
        self.hidden = True
        self.save()

    class Meta:
        # Presumably, you can only have one contract for the same person, offering, and account/position.
        unique_together = (('sessional', 'account', 'offering'),)


