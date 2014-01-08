# Django
from django.db import models


# Third-Party
from autoslug import AutoSlugField
from django_countries.fields import CountryField
from jsonfield import JSONField


# CourSys
from courselib.slugs import make_slug
from courselib.json_fields import getter_setter


# Built-in
import datetime
import decimal

DECIMAL_ZERO = decimal.Decimal('0.00')


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
    institution = models.CharField(max_length=128)
    config = JSONField(null=False, blank=False, default={})
    status = models.CharField(max_length=4, choices=STATUS_CHOICES, default='DISA')
    # TODO What if conversion rules are mixed between discrete and continuous (is that possible?)
    scale = models.CharField(max_length=4, choices=SCALE_CHOICES, default='DISC')

    def _auto_slug(self):
        return make_slug("%s-%s" %(self.institution, self.country))    
    slug = AutoSlugField(populate_from=_auto_slug, null=False, editable=False)

    def __unicode__(self):
        return "%s, %s" %(self.institution, self.country)

    class Meta:
        unique_together = ("country", "institution")


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

# TODO Do conversion rules have to apply to specific courses?  requirements.txt mentions course title as a user input field.
class DiscreteRule(models.Model):
    """
    Discrete GPA Conversion Rule represents the conversions
    of grades from a complete discrete set of possible grade
    values.  For example, [Chicken, Duck, Goose] is the complete
    set of grade values for the lookups.  Each value is then
    mapped to an SFU transfer value (one of the options in the
    TRANSFER_VALUES tuple.
    """
    grade_source = models.ForeignKey('GradeSource')
    lookup_value = models.CharField(max_length=64)
    transfer_value = models.DecimalField(max_digits=5,
                                         decimal_places=2,
                                         default=DECIMAL_ZERO,
                                         choices=TRANSFER_VALUES)
    
    def __unicode__(self):
        return "%s:%s :: %s:SFU" %(self.lookup_value,
                                   self.grade_source,
                                   self.transfer_value)


class ContinuousRule(models.Model):
    """
    Continuous GPA Conversion Rule represents the
    conversions with continuous lookup ranges such as
    90-100 (A), 80-89.99 (B), 70-79.99 (C).

    Inclusion is calculated using the lower bound, so
    for example: score of <= 90 is considered an A, 89.99 is
    still considered a B.
    """
    grade_source = models.ForeignKey('GradeSource')
    lookup_lbound = models.DecimalField(max_digits=5,
                                        decimal_places=2,
                                        choices=LBOUND_VALUES)
    transfer_value = models.DecimalField(max_digits=5,
                                         decimal_places=2,
                                         default=DECIMAL_ZERO,
                                         choices=TRANSFER_VALUES)

    def __unicode__(self):
        return "%s:%s :: %s and up:SFU" %(self.lookup_lbound,
                                          self.grade_source,
                                          self.transfer_value)


