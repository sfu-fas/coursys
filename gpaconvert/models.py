import decimal

from django.db import models

from autoslug import AutoSlugField
from django_countries.fields import CountryField
from jsonfield import JSONField

from courselib.slugs import make_slug

from gpaconvert.utils import get_object_or_None

DECIMAL_ZERO = decimal.Decimal('0.00')


class GradeSourceManager(models.Manager):
    def active(self):
        qs = self.get_query_set()
        return qs.filter(status='ACTI')


class GradeSource(models.Model):
    """
    The source of a set of user grades, may be an institution in
    a specific country.  No two institutions in the same country may
    have the same name.
    """
    SCALE_CHOICES = (
        ('DISC', 'DISCRETE'),
        ('CONT', 'CONTINUOUS'),
    )
    STATUS_CHOICES = (
        ('ACTI', 'ACTIVE'),
        ('DISA', 'DISABLED'),
    )
    country = CountryField()
    institution = models.CharField(max_length=128, verbose_name="Institution/Scale Name")
    config = JSONField(null=False, blank=False, default={})
    status = models.CharField(max_length=4, choices=STATUS_CHOICES, default='DISA')
    scale = models.CharField(max_length=4, choices=SCALE_CHOICES, default='DISC')

    def _auto_slug(self):
        return make_slug("%s-%s" % (self.institution, self.country))
    slug = AutoSlugField(populate_from=_auto_slug, null=False, editable=False)

    objects = GradeSourceManager()

    def __unicode__(self):
        return "%s, %s" % (self.institution, self.country)

    def delete(self):
        raise NotImplementedError("It's a bad thing to delete stuff")

    def get_rule(self, grade):
        """
        Returns the DiscreteRule or ContinuousRule instance that goes with the given grade.
        """

        if self.scale == 'DISC':
            rule = get_object_or_None(self.discrete_rules, lookup_value=grade)
        else:
            # TODO: Make this nicer somehow.
            rules = self.continuous_rules.filter(lookup_lbound__lte=grade)
            if rules.count():
                rule = rules.order_by('-lookup_lbound').first()
            else:
                rule = None

        return rule

    class Meta:
        unique_together = (("country", "institution"),)


# SFU Grade Scale
# Refer to: http://www.sfu.ca/continuing-studies/programs/resources/grading-scale.html
LBOUND_VALUES = (
    (decimal.Decimal('95.00'), 'A+'),
    (decimal.Decimal('90.00'), 'A'),
    (decimal.Decimal('85.00'), 'A-'),
    (decimal.Decimal('80.00'), 'B+'),
    (decimal.Decimal('75.00'), 'B'),
    (decimal.Decimal('70.00'), 'B-'),
    (decimal.Decimal('65.00'), 'C+'),
    (decimal.Decimal('60.00'), 'C'),
    (decimal.Decimal('55.00'), 'C-'),
    (decimal.Decimal('50.00'), 'D'),
    (decimal.Decimal('0.00'), 'F'),
)

# SFU GPA Scale
# Refer to: http://www.sfu.ca/students-resources/NDforms/calc1.html
TRANSFER_VALUES = (
    (decimal.Decimal('4.33'), 'A+'),
    (decimal.Decimal('4.00'), 'A'),
    (decimal.Decimal('3.67'), 'A-'),
    (decimal.Decimal('3.33'), 'B+'),
    (decimal.Decimal('3.00'), 'B'),
    (decimal.Decimal('2.67'), 'B-'),
    (decimal.Decimal('2.33'), 'C+'),
    (decimal.Decimal('2.00'), 'C'),
    (decimal.Decimal('1.67'), 'C-'),
    (decimal.Decimal('1.00'), 'D'),
    (decimal.Decimal('0.00'), 'F'),
)

from grades.models import GPA_GRADE_CHOICES, LETTER_POSITION
TRANSFER_VALUES = GPA_GRADE_CHOICES
#GPA_LOOKUP = {}
#assert dict(TRANSFER_VALUES).keys() == GPA_LOOKUP.keys()



# TODO Why not create an abstract base class for conv. rules, there are 2 redundant fields and many redundant class methods. [No reason: go for it]
# TODO Do conversion rules have to apply to specific courses?  requirements.txt mentions course title as a user input field. [don't care]
class Rule(models.Model):
    """
    Base Conversion rule for GPA Calculator.  This model is
    abstract, and should be inherited for Discrete and Continuous
    Conversion Rules.
    """
    grade_source = models.ForeignKey('GradeSource')
    transfer_value = models.CharField(max_length=2,
                                      null=False,
                                      blank=False,
                                      choices=TRANSFER_VALUES)

    class Meta:
        abstract = True


class DiscreteRule(models.Model):
    """
    Discrete GPA Conversion Rule represents the conversions
    of grades from a complete discrete set of possible grade
    values.  For example, [Chicken, Duck, Goose] is the complete
    set of grade values for the lookups.  Each value is then
    mapped to an SFU transfer value (one of the options in the
    TRANSFER_VALUES tuple.
    """
    grade_source = models.ForeignKey('GradeSource', related_name='discrete_rules')
    lookup_value = models.CharField(max_length=64)
    transfer_value = models.CharField(max_length=2,
                                      null=False, blank=False,
                                      choices=TRANSFER_VALUES)

    def __unicode__(self):
        return "%s:%s :: %s:SFU" % (self.lookup_value,
                                    self.grade_source,
                                    self.transfer_value)

    def delete(self):
        raise NotImplementedError("It's a bad thing to delete stuff")

    class Meta:
        unique_together = ("grade_source", "lookup_value")


class ContinuousRule(models.Model):
    """
    Continuous GPA Conversion Rule represents the
    conversions with continuous lookup ranges such as
    90-100 (A), 80-89.99 (B), 70-79.99 (C).

    Inclusion is calculated using the lower bound, so
    for example: score of <= 90 is considered an A, 89.99 is
    still considered a B.
    """
    grade_source = models.ForeignKey('GradeSource', related_name='continuous_rules')
    lookup_lbound = models.DecimalField(max_digits=8,
                                        decimal_places=2,
                                        verbose_name="Lookup lower bound")
    transfer_value = models.CharField(max_length=2,
                                      null=False, blank=False,
                                      choices=TRANSFER_VALUES)

    def __unicode__(self):
        return "%s:%s :: %s and up:SFU" % (self.lookup_lbound,
                                           self.grade_source,
                                           self.transfer_value)

    # TODO should conversion rules have a mute/unmute flag instead of delete?  Delete method causes issues for formsets.
    def delete(self):
        raise NotImplementedError("It's a bad thing to delete stuff")

    class Meta:
        unique_together = (("grade_source", "lookup_lbound"),)


class UserArchive(models.Model):
    """
    Model to encapsulate a user's gpa calculation event.
    The user may obtain an anonymous URL to go back to the
    calculations at any time, or to share with anyone.
    """
    slug = models.SlugField(max_length=64, unique=True)
    data = JSONField(blank=False, null=False, default={})
    # Defaults
    # TODO decide how the calculations should be layed out in the JSON Field?
    # 'calculations': [
    #   {'queensland-university-au': [
    #       ('MATH100', 'Very Good', 'A+'),
    #       ('COGS100', 'Very Good', 'A+'),
    #   }
    #]

    def __unicode__(self):
        return "Calculation Archive: %s" %self.slug

