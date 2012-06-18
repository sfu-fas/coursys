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
    # active = models.BooleanField(default = False, help_text="The currently-active plan for this semester.")
    slug = AutoSlugField(populate_from='name', null=False, editable=False, unique_with='semester')
    unit = models.ForeignKey(Unit, help_text='The academic unit that owns this course plan')

    def get_absolute_url(self):
        return reverse('planning.views.view_semester_plan', kwargs={'semester': self.semester.name})

    def save(self, *args, **kwargs):
        super(SemesterPlan, self).save(*args, **kwargs)
        # if self.active:
        #     other_plans = SemesterPlan.objects.filter(semester=self.semester, active=True).exclude(pk = self.id)
        #     for other_plan in other_plans:
	       #  other_plan.active = False
        #         super(SemesterPlan, other_plan).save(*args, **kwargs)
            
        #     if self.visibility == 'ADMI':
        #         mem_list = Role.objects.filter(role='PLAN').order_by('person')
        #     elif self.visibility == 'INST':
        #         mem_list = Role.objects.filter(role__in=['FAC', 'SESS', 'PLAN']).order_by('person')
        #     elif self.visibility == 'ALL':
        #         mem_list = Member.objects.filter().order_by('person')

        #     mem_set = set([i.person for i in mem_list])
        #     for m in mem_set:
        #         n = NewsItem(user=m, author=None, source_app="planning", title="Course plan: %s for %s is available" % (self.name, self.semester), content="%s for %s has been released" % (self.name, self.semester), url=self.get_absolute_url())
        #         n.save()

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
        unique_together = (('plan', 'course', 'section'),)
    def name(self):
        return "%s %s %s" % (self.course.subject, self.course.number, self.section)


class MeetingTime(models.Model):
    offering = models.ForeignKey(PlannedOffering, null=False)
    weekday = models.PositiveSmallIntegerField(null=False, choices=WEEKDAY_CHOICES,
        help_text='Day of week of the meeting')
    start_time = models.TimeField(null=False, help_text='Start time of the meeting')
    end_time = models.TimeField(null=False, help_text='End time of the meeting')
    room = models.CharField(max_length=20, help_text='Room (or other location) for the meeting')

    class Meta:
        ordering = ['offering', 'weekday']