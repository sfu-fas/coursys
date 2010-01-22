from django.db import models
from autoslug import AutoSlugField
from timezones.fields import TimeZoneField
from coredata.models import Member, CourseOffering

FLAG_CHOICES = [
    ('NOGR', 'no grade'),
    ('GRAD', 'graded'), 
    ('EXCU', 'excused'), 
    ('DISH', 'academic dishonesty') ]
FLAGS = dict(FLAG_CHOICES)

ACTIVITY_TYPES = ['numericactivity', 'letteractivity']

class Activity(models.Model):
    """
    Generic activity (i.e. column in the gradebook that can have a value assigned for each student).
    This should never be instantiated directly: only its sublcasses should.
    
    When retrieving a collection of Activity objects, check their types like this:
        activity = ...
        if has_attr(activity, 'numericactivity'):
            # we have a NumericActivity
            activity = activity.numericactivity
            # do things that use the NumericActivity instance
            ...  
    """
    name = models.CharField(max_length=30, help_text='Name of the activity.')
    short_name = models.CharField(max_length=15, help_text='Short-form name of the activity.')
    slug = AutoSlugField(populate_from='short_name', null=False, editable=False)
    percent = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    offering = models.ForeignKey(CourseOffering)

    def __unicode__(self):
        return "%s" % (self.name)
    class Meta:
        verbose_name_plural = "activities"
        unique_together = (("offering", "name"), ("offering", "short_name"))

class NumericActivity(Activity):
    """
    Activity with a numeric mark
    """
    max_grade = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        verbose_name_plural = "numeric activities"

class LetterActivity(Activity):
    """
    Activity with a letter grade
    """
    class Meta:
        verbose_name_plural = "letter activities"

class CalculatedNumericActivity(Activity):
    """
    Activity with a calcualted numeric mark
    """
    formula = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "calculated numeric activities"

class CalculatedLetterActivity(Activity):
    source_activity = models.ForeignKey(Activity, related_name="source")
    exam_activity = models.ForeignKey(Activity, related_name="exam")

class LetterCuttoff(models.Model):
    pass

class NumericGrade(models.Model):
    """
    Individual grade for a NumericActivity.
    """
    typed_activity = models.ForeignKey(NumericActivity, null=False)
    member = models.ForeignKey(Member, null=False)

    value = models.DecimalField(max_digits=5, decimal_places=2)
    flag = models.CharField(max_length=4, null=False, choices=FLAG_CHOICES, help_text='Status of the grade')
