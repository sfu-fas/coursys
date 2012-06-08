from django.db import models
from coredata.models import Person, Role, Semester, COMPONENT_CHOICES, CAMPUS_CHOICES, WEEKDAY_CHOICES, Member, Unit
from django.forms import ModelForm
from autoslug import AutoSlugField
from dashboard.models import *
from django.core.urlresolvers import reverse


class Course(models.Model):
    """
    A course, e.g. CMPT 120
    
    More generic than a CourseOffering from coredata, which describes something like CMPT 120 D100 in spring 2011.
    """
    subject = models.CharField(max_length=4, null=False, db_index=True,
        help_text='Subject code, like "CMPT" or "FAN".')
    number = models.CharField(max_length=4, null=False, db_index=True,
        help_text='Course number, like "120" or "XX1".')
    title = models.CharField(max_length=80, help_text='The course title.')
    unit = models.ForeignKey(Unit, help_text='The academic unit that owns this course.')
    
    class Meta:
        ordering = ['subject', 'number']
        unique_together = (('subject', 'number'),)
    
    def __unicode__(self):
        return "%s %s (%s)" % (self.subject, self.number, self.title)
    def short_str(self):
        return "%s %s" % (self.subject, self.number)
        
    def __cmp__(self, other):
        if isinstance(other, Course):
            return cmp(str(self), str(other))
        return NotImplemented


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
    intentionfull = models.BooleanField(default = False)

    class Meta:
        ordering = ['-semester', 'instructor']
        unique_together = (('instructor', 'semester'),)
        
    def __unicode__(self):
        return "%s: %d (%s)" % (self.instructor, self.count, self.semester.label())
    
    def is_full(self, semester_plan):
        return semester_plan.plannedoffering_set.filter(instructor=self.instructor).count() >= self.count
         


VISIBILITY_CHOICES = [
    ('ADMI', 'Administrator Only'),
    ('INST', 'Instructors'), 
    ('ALL', 'Everybody')]


class SemesterPlan(models.Model):
    semester = models.ForeignKey(Semester)
    name = models.CharField(max_length=70, help_text="A name to help you remeber which plan this is.")
    visibility = models.CharField(max_length=4, choices=VISIBILITY_CHOICES, default="ADMI", help_text="Who can see this plan?")
    active = models.BooleanField(default = False, help_text="The currently-active plan for this semester.")
    slug = AutoSlugField(populate_from='name', null=False, editable=False, unique_with='semester')
    unit = models.ForeignKey(Unit, help_text='The academic unit that owns this semester plan')

    def get_absolute_url(self):
        return reverse('planning.views.view_semester_plan', kwargs={'semester': self.semester.name})

    def save(self, *args, **kwargs):
        super(SemesterPlan, self).save(*args, **kwargs)
        if self.active:
            other_plans = SemesterPlan.objects.filter(semester=self.semester, active=True).exclude(pk = self.id)
            for other_plan in other_plans:
	        other_plan.active = False
                super(SemesterPlan, other_plan).save(*args, **kwargs)
            
            if self.visibility == 'ADMI':
                mem_list = Role.objects.filter(role='PLAN').order_by('person')
            elif self.visibility == 'INST':
                mem_list = Role.objects.filter(role__in=['FAC', 'SESS', 'PLAN']).order_by('person')
            elif self.visibility == 'ALL':
                mem_list = Member.objects.filter().order_by('person')

            mem_set = set([i.person for i in mem_list])
            for m in mem_set:
                n = NewsItem(user=m, author=None, source_app="planning", title="Semester plan: %s for %s is available" % (self.name, self.semester), content="%s for %s has been released" % (self.name, self.semester), url=self.get_absolute_url())
                n.save()

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

    class Meta:
        ordering = ['plan', 'course', 'campus']
        unique_together = (('plan', 'course', 'section'),)
    

class MeetingTime(models.Model):
    offering = models.ForeignKey(PlannedOffering, null=False)
    weekday = models.PositiveSmallIntegerField(null=False, choices=WEEKDAY_CHOICES,
        help_text='Day of week of the meeting')
    start_time = models.TimeField(null=False, help_text='Start time of the meeting')
    end_time = models.TimeField(null=False, help_text='End time of the meeting')
    room = models.CharField(max_length=20, help_text='Room (or other location) for the meeting')

    class Meta:
        ordering = ['offering', 'weekday']


