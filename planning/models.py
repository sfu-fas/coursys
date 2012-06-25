from django.db import models
from coredata.models import Person, Role, Semester, COMPONENT_CHOICES, CAMPUS_CHOICES, WEEKDAY_CHOICES, Member, Unit, Course
from django.forms import ModelForm
from autoslug import AutoSlugField
from dashboard.models import *
from django.core.urlresolvers import reverse


COURSE_STATUS_CHOICES = [
    ('OPEN', 'Open'),
    ('HIDE', 'Hidden')]

class PlanningCourse(Course):
    owner = models.ForeignKey(Unit, null=False)
    status = models.CharField(max_length=4, choices=COURSE_STATUS_CHOICES, default="OPEN", help_text="Status of this course")

    class Meta:
        unique_together = ()
        ordering = ('subject', 'number')
    

class TeachingCapability(models.Model):
    instructor = models.ForeignKey(Person, null=False)
    course = models.ForeignKey(Course, null=False)
    note = models.TextField(null=True, blank=True, default="", help_text="Additional information for those doing the course planning.")

    class Meta:
        ordering = ['instructor', 'course']
        unique_together = (('instructor','course'),)
        
    def __unicode__(self):
        return "%s - %s" % (self.instructor, self.course)


class TeachingIntention(models.Model):
    instructor = models.ForeignKey(Person, null=False)
    semester = models.ForeignKey(Semester, null=False)
    count = models.PositiveSmallIntegerField(help_text="The number of courses the instructor plans to teach in this semester.")    
    note = models.TextField(null=True, blank=True, default="", help_text="Additional information for those doing the course planning.")
    intentionfull = models.BooleanField(default=False)

    class Meta:
        ordering = ['-semester', 'instructor']
        unique_together = (('instructor', 'semester'),)
        
    def __unicode__(self):
        return "%s: %d (%s)" % (self.instructor, self.count, self.semester.label())
    
    def is_full(self, semester_plan):
        return semester_plan.plannedoffering_set.filter(instructor=self.instructor).count() >= self.count


VISIBILITY_CHOICES = [
    ('ADMI', 'Administrators Only'),
    ('INST', 'Instructors'), 
    ('ALL', 'Everyone')]


class SemesterPlan(models.Model):
    semester = models.ForeignKey(Semester)
    name = models.CharField(max_length=70, help_text="A name to help you remeber which plan this is.")
    visibility = models.CharField(max_length=4, choices=VISIBILITY_CHOICES, default="ADMI", help_text="Who can see this plan?")
    slug = AutoSlugField(populate_from='name', null=False, editable=False, unique_with='semester')
    unit = models.ForeignKey(Unit, help_text='The academic unit that owns this course plan')

    def get_absolute_url(self):
        return reverse('planning.views.view_plan', kwargs={'semester': self.semester.name})

    def save(self, *args, **kwargs):
        super(SemesterPlan, self).save(*args, **kwargs)

    class Meta:
        ordering = ['semester', 'name']
        unique_together = (('semester', 'name'),)


class PlannedOffering(models.Model):
    plan = models.ForeignKey(SemesterPlan)
    course = models.ForeignKey(Course, null=False)
    section = models.CharField(max_length=4, blank=False, null=False, default='',
        help_text='Section should be in the form "C100" or "D103".')
    component = models.CharField(max_length=3, null=False, choices=COMPONENT_CHOICES, default="LEC",
        help_text='Component of the course, like "LEC" or "LAB".')
    campus = models.CharField(max_length=5, choices=CAMPUS_CHOICES, null=False)
    enrl_cap = models.PositiveSmallIntegerField(null=True, blank=True)
    instructor = models.ForeignKey(Person, null=True, blank=True)
    slug = AutoSlugField(populate_from='name', null=False, editable=False, unique_with='section')

    class Meta:
        ordering = ['plan', 'course', 'campus']
        unique_together = ('plan', 'course', 'section')

    def name(self):
        return "%s %s %s" % (self.course.subject, self.course.number, self.section)


class MeetingTime(models.Model):
    offering = models.ForeignKey(PlannedOffering, null=False)
    weekday = models.PositiveSmallIntegerField(null=False, choices=WEEKDAY_CHOICES,
        help_text='Day of week of the meeting')
    start_time = models.TimeField(null=False, help_text='Start time of the meeting, e.g. "11:30".', verbose_name="Start time")
    end_time = models.TimeField(null=False, help_text='End time of the meeting, e.g. "12:20".')
    room = models.CharField(max_length=20, help_text='Room (or other location) for the meeting')

    class Meta:
        ordering = ['offering', 'weekday']
        
EQUIVALENT_STATUS_CHOICES = (
                             ('CONF', 'Confirmed'),
                             ('UNCO', 'Unconfirmed')
                             )
        
class TeachingEquivalent(models.Model):
    """
    A teaching equivalent for instructors to record teaching credits (supports rationals)
    """
    instructor = models.ForeignKey(Person)
    semester = models.ForeignKey(Semester)
    credits_numerator = models.IntegerField(help_text='The numerator of a fractional credit')
    credits_denominator = models.IntegerField(help_text='The denomiator of a fractional credit')
    summary = models.CharField(max_length='100', help_text='What is this teaching equivalent for?')
    comment = models.TextField(blank=True, null=True, help_text='Any information that should be included')
    status = models.CharField(max_length=4, choices=EQUIVALENT_STATUS_CHOICES)
    
    
    