from django.db import models
from coredata.models import Person, Role, Semester, COMPONENT_CHOICES, CAMPUS_CHOICES, WEEKDAY_CHOICES 
from django.forms import ModelForm
from django.template.defaultfilters import slugify


class Course(models.Model):
    """
    A course, e.g. CMPT 120
    
    More generic than a CourseOffering from coredata, which describes something like CMPT 120 D100 in spring 2011.
    """
    subject = models.CharField(max_length=4, null=False, db_index=True,
        help_text='Subject code, like "CMPT" or "FAN".')
    number = models.CharField(max_length=4, null=False, db_index=True,
        help_text='Course number, like "120" or "XX1".')
    title = models.CharField(max_length=30, help_text='The course title.')
    
    class Meta:
        ordering = ['subject', 'number']
        unique_together = (('subject', 'number'),)
	
    def __unicode__(self):
        return "%s %s (%s)" % (self.subject, self.number, self.title)
        
    def __cmp__(self, other):
        if isinstance(other, Course):
            return cmp(str(self), str(other))
        return NotImplemented


class TeachingCapability(models.Model):
    instructor = models.ForeignKey(Person, null=False)
    course = models.ForeignKey(Course, null=False)

    class Meta:
        ordering = ['instructor', 'course']
        unique_together = (('instructor','course'),)
        
    def __unicode__(self):
        return "%s - %s" % (self.instructor, self.course)

class TeachingIntention(models.Model):
    instructor = models.ForeignKey(Person, null=False)
    semester = models.ForeignKey(Semester, null=False)
    count = models.PositiveSmallIntegerField(help_text="the number of courses the instructor should teach in the semester.")    

    class Meta:
        ordering = ['-semester', 'instructor']
        unique_together = (('instructor', 'semester'),)
        
    def __unicode__(self):
        return "%s: %d (%s)" % (self.instructor, self.count, self.semester.label())

class PlannedOffering(models.Model):
    #plan = models.ForeignKey(SemesterPlan)
    course = models.ForeignKey(Course, null=False)
    section = models.CharField(max_length=4, blank=True, default='',
        help_text='Section should be in the form "C100" or "D103".')
    component = models.CharField(max_length=3, null=False, choices=COMPONENT_CHOICES, default="LEC",
        help_text='Component of the course, like "LEC" or "LAB".')
    campus = models.CharField(max_length=5, choices=CAMPUS_CHOICES, null=False)
    enrl_cap = models.PositiveSmallIntegerField(null=True, blank=True)
    instructor = models.ForeignKey(Person, null=True, blank=True)

    class Meta:
        ordering = ['course', 'section', 'campus']
        unique_together = (('course', 'section'),)
    

class MeetingTime(models.Model):
    offering = models.ForeignKey(PlannedOffering, null=False)
    weekday = models.PositiveSmallIntegerField(null=False, choices=WEEKDAY_CHOICES,
        help_text='Day of week of the meeting')
    start_time = models.TimeField(null=False, help_text='Start time of the meeting')
    end_time = models.TimeField(null=False, help_text='End time of the meeting')
    room = models.CharField(max_length=20, help_text='Room (or other location) for the meeting')

    class Meta:
        ordering = ['weekday']


#class SemesterPlan(models.Model):
    #semester = models.ForeignKey(Semester)
    #visibility = models.

