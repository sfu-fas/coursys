import decimal

from django.db import models
from django.core.urlresolvers import reverse

from autoslug import AutoSlugField
from django_countries.fields import CountryField
from courselib.json_fields import JSONField

from courselib.slugs import make_slug
from grades.models import GPA_GRADE_CHOICES

from gpaconvert.utils import get_object_or_None

DECIMAL_ZERO = decimal.Decimal('0.00')
DECIMAL_HUNDRED = decimal.Decimal('100.00')

# SFU GPA Scale: http://www.sfu.ca/students-resources/NDforms/calc1.html
GRADE_POINTS = {
    'A+': decimal.Decimal('4.33'),
    'A': decimal.Decimal('4.00'),
    'A-': decimal.Decimal('3.67'),
    'B+': decimal.Decimal('3.33'),
    'B': decimal.Decimal('3.00'),
    'B-': decimal.Decimal('2.67'),
    'C+': decimal.Decimal('2.33'),
    'C': decimal.Decimal('2.00'),
    'C-': decimal.Decimal('1.67'),
    'D': decimal.Decimal('1.00'),
    'F': decimal.Decimal('0.00'),
}
assert set(GRADE_POINTS.keys()) == set(dict(GPA_GRADE_CHOICES).keys())


class GradeSourceManager(models.Manager):
    def active(self):
        qs = self.get_queryset()
        return qs.filter(status='ACTI')


class GradeSource(models.Model):
    """
    The source of a set of user grades, may be an institution in
    a specific country.  No two institutions in the same country may
    have the same name.
    """
    SCALE_CHOICES = (
        ('DISC', 'Discrete: fixed set of allowed grades'),
        ('CONT', 'Continuous: numeric grade range'),
    )
    STATUS_CHOICES = (
        ('ACTI', 'Active'),
        ('DISA', 'Disabled: invisible to students'),
    )
    country = CountryField()
    institution = models.CharField(max_length=128, verbose_name="Institution/Scale Name")
    config = JSONField(null=False, blank=False, default={})
    status = models.CharField(max_length=4, choices=STATUS_CHOICES, default='ACTI')
    scale = models.CharField(max_length=4, choices=SCALE_CHOICES, default='DISC')

    # Only used for Continuous rules
    lower_bound = models.DecimalField(max_digits=8,
                                      decimal_places=2,
                                      default=DECIMAL_ZERO,
                                      help_text="Only used for continuous grade sources")
    upper_bound = models.DecimalField(max_digits=8,
                                      decimal_places=2,
                                      default=DECIMAL_HUNDRED,
                                      help_text="Only used for continuous grade sources")

    def _auto_slug(self):
        return make_slug("%s-%s" % (self.institution, self.country))
    slug = AutoSlugField(populate_from='_auto_slug', null=False, editable=False)

    objects = GradeSourceManager()

    class Meta:
        unique_together = (("country", "institution"),)
        ordering = ('institution', 'country')

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
            rules = (self.continuous_rules.filter(lookup_lbound__lte=grade)
                                          .order_by('-lookup_lbound'))
            if rules:
                rule = rules.first()
            else:
                rule = None

        return rule

    def all_discrete_grades(self):
        """
        A all input grades we know about for a discrete scale, sorted in a reasonable way.
        """
        assert self.scale == 'DISC'
        rules = list(DiscreteRule.objects.filter(grade_source=self))
        rules.sort(key=lambda r: r.sortkey(), reverse=True)
        return rules

    def all_discrete_grades_str(self):
        return ', '.join(r.lookup_value for r in self.all_discrete_grades())


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
                                      choices=GPA_GRADE_CHOICES)

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
                                      choices=GPA_GRADE_CHOICES)

    class Meta:
        unique_together = (("grade_source", "lookup_value"),)

    def __unicode__(self):
        return "%s:%s :: %s:SFU" % (self.lookup_value,
                                    self.grade_source,
                                    self.transfer_value)

    @property
    def grade_points(self):
        return GRADE_POINTS[self.transfer_value]

    def sortkey(self):
        """
        a key to sensibly sort discrete rules
        """
        return (self.grade_points, self.lookup_value)



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
                                      choices=GPA_GRADE_CHOICES)

    def __unicode__(self):
        return "%s:%s :: %s and up:SFU" % (self.lookup_lbound,
                                           self.grade_source,
                                           self.transfer_value)

    @property
    def grade_points(self):
        return GRADE_POINTS[self.transfer_value]

    class Meta:
        unique_together = (("grade_source", "lookup_lbound"),)


class UserArchive(models.Model):
    """
    Model to encapsulate a user's gpa calculation event.
    The user may obtain an anonymous URL to go back to the
    calculations at any time, or to share with anyone.
    """
    grade_source = models.ForeignKey(GradeSource)
    slug = models.SlugField(max_length=64, unique=True)
    data = JSONField(blank=False, null=False, default={})
    # Defaults
    # data field should store the raw data dump from the RuleFormSet.
    # Then the form can be repopulated with ease.

    def __unicode__(self):
        return "Calculation Archive: %s" % self.slug

    def get_absolute_url(self):
        return reverse("view_saved_grades", args=[self.grade_source.slug, self.slug])
