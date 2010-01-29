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

ACTIVITY_STATUS_CHOICES = [
    ('RLS', 'released'),
    ('URLS', 'unreleased'),
    ('INVI', 'invisible') ]
ACTIVITY_STATUS = dict(ACTIVITY_STATUS_CHOICES)

LETTER_GRADE_CHOICES = [
    ('A+', 'A+ - Excellent performance'),
    ('A', 'A - Excellent performance'),
    ('A-', 'A- - Excellent performance'),
    ('B+', 'B+ - Good performance'),
    ('B', 'B - Good performance'),
    ('B-', 'B- - Good performance'),
    ('C+', 'C+ - Satisfactory performance'),
    ('C', 'C - Satisfactory performance'),
    ('C-', 'C- - Marginal performance'),
    ('D', 'D - Marginal performance'),
    ('F', 'F - Fail(Unsatisfactory performance)'),
    ('FD', 'FD - Fail(Academic discipline)'),
    ('N', 'N - Did not write exam or did not complete course'),
    ('P', 'P - Satisfactory performance or better (pass, ungraded)'),
    ('W', 'W - Withdrawn'),
    ('AE', 'AE - Aegrotat standing, compassionate pass'),
    ('AU', 'AU - Audit'),
    ('CC', 'CC - Course challenge'),
    ('CF', 'CF - Course challenge fail'),
    ('CN', 'CN - Did not complete challenge'),
    ('CR', 'CR - Credit without grade'),
    ('FX', 'FX - Formal exchange'),
    ('WD', 'WD - Withdrawal'),
    ('WE', 'WE - Withdrawal under extenuating circumstances'),
    ('DE', 'DE - Deferred grade'),
    ('GN', 'GN - Grade not reported'),
    ('IP', 'IP - In progress') ]
LETTER_GRADE = dict(LETTER_GRADE_CHOICES)

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
    status = models.CharField(max_length=4, null=False, choices=ACTIVITY_STATUS_CHOICES, help_text='Activity status.')
    due_date = models.DateTimeField(blank=True, null=True, help_text='Activity due date')
    percent = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    
    offering = models.ForeignKey(CourseOffering)

    def __unicode__(self):
        return "%s - %s" % (self.offering, self.name)
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

class CalNumericActivity(NumericActivity):
    """
    Activity with a calculated numeric grade which is the final numeric grade of the course offering
    """
    formula = models.CharField(max_length=250, help_text='parsed formula to calculate final numeric grade')

    class Meta:
        verbose_name_plural = "cal numeric activities"

class CalLetterActivity(LetterActivity):
    """
    Activity with a calculated letter grade which is the final letter grade of the course offering
    """
    numeric_activity = models.ForeignKey(NumericActivity, related_name='numeric_source_set')
    exam_activity = models.ForeignKey(Activity, blank=True, null=True, related_name='exam_set')
    letter_cutoff_formula = models.CharField(max_length=250, help_text='parsed formula to calculate final letter grade')
    
    class Meta:
        verbose_name_plural = 'cal letter activities'

class NumericGrade(models.Model):
    """
    Individual numeric grade for a NumericActivity.
    """
    activity = models.ForeignKey(NumericActivity, null=False)
    member = models.ForeignKey(Member, null=False)

    value = models.DecimalField(max_digits=5, decimal_places=2, default = 0)
    flag = models.CharField(max_length=4, null=False, choices=FLAG_CHOICES, help_text='Status of the grade', default = 'NOGR')
    
    def __unicode__(self):
        return "Member[%s]'s grade[%s] for [%s]" % (self.member.person.userid, self.value, self.activity)
    
    class Meta:
        unique_together = (('activity', 'member'),)
    
class LetterGrade(models.Model):
    """
    Individual letter grade for a LetterActivity
    """
    activity = models.ForeignKey(LetterActivity, null=False)
    member = models.ForeignKey(Member, null=False)
    
    letter_grade = models.CharField(max_length=2, null=False, choices=LETTER_GRADE_CHOICES)
    flag = models.CharField(max_length=4, null=False, choices=FLAG_CHOICES, help_text='Status of the grade')
    
    def __unicode__(self):
        return "Member[%s]'s letter grade[%s] for [%s]" % (self.member.person.userid, self.letter_grade, self.typed_activity)
    
    class Meta:
        unique_together = (('activity', 'member'), )
