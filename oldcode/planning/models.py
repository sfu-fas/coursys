from django.db import models
from coredata.models import Person, Semester, COMPONENT_CHOICES, CAMPUS_CHOICES, WEEKDAY_CHOICES, \
        Unit, Course, CourseOffering, Member
from autoslug import AutoSlugField
from django.core.urlresolvers import reverse
from courselib.json_fields import JSONField
from fractions import Fraction
import datetime

COURSE_STATUS_CHOICES = [
    ('OPEN', 'Open'),
    ('HIDE', 'Hidden')]


class PlanningCourse(models.Model):
    """
    This does not inherit from coredata.models due to inheritance issues with the
    unique_together property.
    """
    subject = models.CharField(max_length=4, null=False, db_index=True,
        help_text='Subject code, like "CMPT" or "FAN".')
    number = models.CharField(max_length=4, null=False, db_index=True,
        help_text='Course number, like "120" or "XX1".')
    title = models.CharField(max_length=30, help_text='The course title.')
    owner = models.ForeignKey(Unit, null=False)
    status = models.CharField(max_length=4, choices=COURSE_STATUS_CHOICES, default="OPEN", help_text="Status of this course")
    slug = AutoSlugField(populate_from=('__unicode__'), null=False, editable=False, unique_with='id')
    config = JSONField(null=False, blank=False, default={})  # addition configuration stuff

    class Meta:
        ordering = ('subject', 'number')

    def __unicode__(self):
        return "%s %s" % (self.subject, self.number)

    def __cmp__(self, other):
        return cmp(self.subject, other.subject) or cmp(self.number, other.number)

    def delete(self, *args, **kwargs):
        raise NotImplementedError("This object cannot be deleted because it is used as a foreign key.")

    def full_name(self):
        return "%s %s - %s" % (self.subject, self.number, self.title)
    
    @classmethod
    def create_for_unit(cls, unit):
        """
        Populate PlanningCourse objects for this unit, with any Course this unit has offered
        in the last two years.
        """
        old_sem = Semester.get_semester(datetime.date.today()-datetime.timedelta(days=365*2))
        offerings = CourseOffering.objects.filter(owner=unit, semester__name__gte=old_sem.name)
        existing = set((pc.subject, pc.number) for pc in PlanningCourse.objects.filter(owner=unit))
        for crs in set(c.course for c in offerings.select_related('course')):
            if (crs.subject, crs.number) not in existing:
                # found a missing PlanningCourse: add it.
                pc = PlanningCourse(subject=crs.subject, number=crs.number, title=crs.title, owner=unit)
                pc.save()
            


class TeachingCapability(models.Model):
    """
    A teaching capability for instructors to record which courses they have the ability to teach.
    """
    instructor = models.ForeignKey(Person, null=False)
    course = models.ForeignKey(Course, null=False)
    note = models.TextField(null=True, blank=True, default="", help_text="Additional information for those doing the course planning.")

    class Meta:
        ordering = ['instructor', 'course']
        unique_together = (('instructor', 'course'),)

    def __unicode__(self):
        return "%s - %s" % (self.instructor, self.course)
    
    @classmethod
    def populate_from_history(cls, person, years=2):
        """
        Create TeachingCapability objects for any courses this person has
        taught in recent years.
        """
        old_sem = Semester.get_semester(datetime.date.today()-datetime.timedelta(days=365*years))
        members = Member.objects.filter(person=person, role='INST', offering__semester__name__gte=old_sem.name)
        courses = set(m.offering.course for m in members.select_related('offering__course'))
        existing = set(tc.course_id for tc in TeachingCapability.objects.filter(instructor=person))
        for crs in courses:
            if crs.id not in existing:
                # found a course that has been taught but not listed as capable
                tc = TeachingCapability(instructor=person, course=crs)
                tc.save()
        
        


class TeachingIntention(models.Model):
    """
    A teaching intention for instructors to record the number of courses they wish to teach in future semesters
    """
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
    """
    A semester plan which holds potential planned offerings.
    """
    semester = models.ForeignKey(Semester)
    name = models.CharField(max_length=70, help_text="A name to help you remeber which plan this is.")
    visibility = models.CharField(max_length=4, choices=VISIBILITY_CHOICES, default="ADMI", help_text="Who can see this plan?")
    slug = AutoSlugField(populate_from='name', null=False, editable=False, unique_with='semester')
    unit = models.ForeignKey(Unit, help_text='The academic unit that owns this course plan')
    config = JSONField(null=False, blank=False, default={})

    def get_absolute_url(self):
        return reverse('planning.views.view_plan', kwargs={'semester': self.semester.name})

    def save(self, *args, **kwargs):
        super(SemesterPlan, self).save(*args, **kwargs)

    class Meta:
        ordering = ['semester', 'name']
        unique_together = (('semester', 'name'),)


class PlannedOffering(models.Model):
    """
    A course offering for a future semester. More generic than coredata.model' CourseOffering.
    """
    plan = models.ForeignKey(SemesterPlan)
    course = models.ForeignKey(Course, null=False)
    section = models.CharField(max_length=4, blank=False, null=False, default='',
        help_text='Section should be in the form "C100" or "D103".')
    component = models.CharField(max_length=3, null=False, choices=COMPONENT_CHOICES, default="LEC",
        help_text='Component of the course, like "LEC" or "LAB".')
    campus = models.CharField(max_length=5, choices=CAMPUS_CHOICES, null=False)
    enrl_cap = models.PositiveSmallIntegerField(null=True, blank=True)
    instructor = models.ForeignKey(Person, null=True, blank=True)
    slug = AutoSlugField(populate_from='__unicode__', null=False, editable=False, unique_with='section')
    notes = models.TextField(null=True, blank=True, default="", help_text="Additional information for cross-listing or other notes")
    config = JSONField(null=False, blank=False, default={})

    class Meta:
        ordering = ['plan', 'course', 'campus']
        unique_together = ('plan', 'course', 'section')

    def __unicode__(self):
        return "%s %s %s" % (self.course.subject, self.course.number, self.section)


class MeetingTime(models.Model):
    """
    A meeting day, time and room for a planned offering. More generic than coredata.models' meeting time.
    """
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
    credits_denominator = models.IntegerField(help_text='The denominator of a fractional credit')
    summary = models.CharField(max_length='100', help_text='What is this teaching equivalent for?')
    comment = models.TextField(blank=True, null=True, help_text='Any information that should be included')
    status = models.CharField(max_length=4, choices=EQUIVALENT_STATUS_CHOICES)

    def get_credits(self):
        return Fraction("%d/%d" % (self.credits_numerator, self.credits_denominator))

    def save(self, *args, **kwargs):
        if not self.status in [status[0] for status in EQUIVALENT_STATUS_CHOICES]:
            raise ValueError('Invalid status')
        super(TeachingEquivalent, self).save(*args, **kwargs)
