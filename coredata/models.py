from django.db import models
from django.template.defaultfilters import slugify
from autoslug import AutoSlugField
from timezones.fields import TimeZoneField
from django.conf import settings
import datetime
from django.core.urlresolvers import reverse

class Person(models.Model):
    """
    A person in the system (students, instuctors, etc.).
    """
    emplid = models.PositiveIntegerField(db_index=True, unique=True, null=False,
        help_text='Employee ID (i.e. student number)')
    userid = models.CharField(max_length=8, null=True, db_index=True, unique=True,
        help_text='SFU Unix userid (i.e. part of SFU email address before the "@").')
    last_name = models.CharField(max_length=32)
    first_name = models.CharField(max_length=32)
    middle_name = models.CharField(max_length=32, null=True)
    pref_first_name = models.CharField(max_length=32)
    
    def __unicode__(self):
        return "%s, %s" % (self.last_name, self.first_name)
    def name(self):
        if self.middle_name:
            return "%s %s %s" % (self.pref_first_name, self.middle_name, self.last_name)
        else:
            return "%s %s" % (self.pref_first_name, self.last_name)
    def email(self):
        return "%s@sfu.ca" % (self.userid)
    class Meta:
        verbose_name_plural = "People"
        ordering = ['last_name', 'first_name', 'userid']


class Semester(models.Model):
    """
    A semester object: not imported, must be created manually.
    """
    label_lookup = {
        '1': 'Spring',
        '4': 'Summer',
        '7': 'Fall',
        }
    name = models.CharField(max_length=4, null=False, db_index=True, unique=True,
        help_text='Semester name should be in the form "1097".')
    start = models.DateField(help_text='First day of classes.')
    end = models.DateField(help_text='Last day of classes.')
    # TODO: validate that there is a SemesterWeek for week #1.
    
    def label(self):
        """
        The human-readable label for the semester, e.g. "Summer 2010".
        """
        name = str(self.name)
        year = 1900 + int(name[0:3])
        semester = self.label_lookup[name[3]]
        return semester + " " + str(year)

    def __unicode__(self):
        return str(self.name)
    
    def week_weekday(self, dt):
        """
        Given a datetime, return the week-of-semester and day-of-week (with 0=Monday).
        """
        # gracefully deal with both date and datetime objects
        if isinstance(dt, datetime.datetime):
            date = dt.date()
        else:
            date = dt

        # find the "base": first known week before the given date
        weeks = list(SemesterWeek.objects.filter(semester=self))
        weeks.reverse()
        base = None
        for w in weeks:
            if w.monday <= date:
                base = w
                break

        if base is None:
            raise ValueError, "Date seems to be before the start of semester."

        diff = date - base.monday
        diff = int(round(diff.days + diff.seconds/86400.0)+0.5) # convert to number of days, rounding off any timezone stuff
        week = base.week + diff//7
        wkday = date.weekday()
        return week, wkday
    
    def duedate(self, wk, wkday, time):
        """
        Calculate duedate based on week-of-semester and weekday.  Provided argument time can be either datetime.time or datetime.datetime: time is copied from this to new duedate.
        """
        # find the "base": first known week before mk
        weeks = list(SemesterWeek.objects.filter(semester=self))
        weeks.reverse()
        base = None
        for w in weeks:
            if w.week <= wk:
                base = w
                break
        
        date = base.monday + datetime.timedelta(days=7*(wk-base.week)+wkday)
        # construct the datetime from date and time.
        dt = datetime.datetime(year=date.year, month=date.month, day=date.day, 
            hour=time.hour, minute=time.minute, second=time.second, microsecond=time.microsecond, tzinfo=time.tzinfo)
        return dt

    class Meta:
        ordering = ['name']


class SemesterWeek(models.Model):
    """
    Starting points for weeks in the semester.
    
    Every semester object needs at least a SemesterWeek for week 1.
    """
    semester = models.ForeignKey(Semester, null=False)
    week = models.PositiveSmallIntegerField(null=False, help_text="Week of the semester (typically 1-13)")
    monday = models.DateField(help_text='Monday of this week.')
    # TODO: validate that monday is really a Monday.
    
    def __unicode__(self):
        return "%s week %i" % (self.semester.name, self.week)
    class Meta:
        ordering = ['semester','week']
        unique_together = (('semester', 'week'))

    
class CourseOffering(models.Model):
    COMPONENT_CHOICES = (
        ('LEC', 'Lecture'),
        ('LAB', 'Lab'),
        ('TUT', 'Tutorial'),
        ('SEM', 'Seminar'),
        ('SEC', 'Section'), # "Section"?  ~= lecture?
        #('OPL', 'Open Lab'),
        #('FLD', 'Field School'),
    )
    COMPONENTS = dict(COMPONENT_CHOICES)
    CAMPUS_CHOICES = (
        ('BRNBY', 'Burnaby Campus'),
        ('SURRY', 'Surrey Campus'),
        ('VANCR', 'Harbour Centre'),
        ('OFFST', 'Off-campus'),
        #('SEGAL', 'Segal Centre'),
        #('GRNORTHW', 'Great Northern Way Campus'),
        #('KAM', 'Kamloops Campus'),
    )
    CAMPUSES = dict(CAMPUS_CHOICES)

    subject = models.CharField(max_length=4, null=False, db_index=True,
        help_text='Subject code, like "CMPT" or "FAN".')
    number = models.CharField(max_length=4, null=False, db_index=True,
        help_text='Course number, like "120" or "XX1".')
    section = models.CharField(max_length=4, null=False,
        help_text='Section should be in the form "C100" or "D103".')
    semester = models.ForeignKey(Semester, null=False)
    component = models.CharField(max_length=3, null=False, choices=COMPONENT_CHOICES,
        help_text='Component of the course, like "LEC" or "LAB".')
    graded = models.BooleanField()
    # need these to join in the SIMS database: don't care otherwise.
    crse_id = models.PositiveSmallIntegerField(null=False, db_index=True)
    class_nbr = models.PositiveSmallIntegerField(null=False, db_index=True)
    
    title = models.CharField(max_length=30, help_text='The course title.')
    #title_long = models.CharField(max_length=80, help_text='The course title (full version).')
    campus = models.CharField(max_length=5, choices=CAMPUS_CHOICES)
    enrl_cap = models.PositiveSmallIntegerField()
    enrl_tot = models.PositiveSmallIntegerField()
    wait_tot = models.PositiveSmallIntegerField()

    members = models.ManyToManyField(Person, related_name="member", through="Member")
    
    def autoslug(self):
        words = [str(s) for s in self.semester, self.subject, self.number, self.section]
        return '-'.join(words)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False)

    def __unicode__(self):
        return "%s %s %s (%s)" % (self.subject, self.number, self.section, self.semester.label())
    def name(self):
        if self.graded:
            return "%s %s %s" % (self.subject, self.number, self.section[:-2])
        else:
            return "%s %s %s" % (self.subject, self.number, self.section)
        
    def get_absolute_url(self):
        return reverse('grades.views.course_info', kwargs={'course_slug': self.slug})
    
    def instructors(self):
        return (m.person for m in self.member_set.filter(role="INST"))
    def tas(self):
        return (m.person for m in self.member_set.filter(role="TA"))
    def student_count(self):
        return self.members.filter(person__role='STUD').count()

    # TODO: week number -> date (of the Monday)
    # TODO: date -> week number

    class Meta:
        ordering = ['-semester', 'subject', 'number', 'section']
        unique_together = (
            ('semester', 'subject', 'number', 'section'),
            ('semester', 'crse_id', 'section'),
            ('semester', 'class_nbr') )


class Member(models.Model):
    """
    "Members" of the course.  Role indicates instructor/student/TA/etc.

    Includes dropped students and non-graded sections (labs/tutorials).  Often want to select with:
        Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(...)
    """
    ROLE_CHOICES = (
        ('STUD', 'Student'),
        ('TA', 'TA'),
        ('INST', 'Instructor'),
        ('APPR', 'Grade Approver'),
        ('DROP', 'Dropped'),
        #('AUD', 'Audit Student'),
    )
    REASON_CHOICES = (
        ('AUTO', 'Automatically added'),
        ('TRU', 'TRU/OU Distance Student'),
        ('TA', 'Additional TA'),
        ('INST', 'Additional Instructor'),
        ('UNK', 'Unknown/Other Reason'),
    )
    CAREER_CHOICES = (
        ('UGRD', 'Undergraduate'),
        ('GRAD', 'Graduate'),
        ('NONS', 'Non-Student'),
    )
    CAREERS = dict(CAREER_CHOICES)
    person = models.ForeignKey(Person, related_name="person")
    offering = models.ForeignKey(CourseOffering)
    role = models.CharField(max_length=4, choices=ROLE_CHOICES)
    credits = models.PositiveSmallIntegerField(null=False, default=3,
        help_text='Number of credits this course is worth.')
    career = models.CharField(max_length=4, choices=CAREER_CHOICES)
    added_reason = models.CharField(max_length=4, choices=REASON_CHOICES)
    def __unicode__(self):
        #if self.person:
        #    return "%s in %s" % (self.person, self.offering)
        #else:
        return "%s (%s) in %s" % (self.person.userid, self.person.emplid, self.offering,)

    class Meta:
        unique_together = (('person', 'offering', 'role'),)
        ordering = ['offering', 'person']


class MeetingTime(models.Model):
    WEEKDAY_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )
    offering = models.ForeignKey(CourseOffering, null=False)
    weekday = models.PositiveSmallIntegerField(null=False, choices=WEEKDAY_CHOICES,
        help_text='Day of week of the meeting')
    start_time = models.TimeField(null=False, help_text='Start time of the meeting')
    end_time = models.TimeField(null=False, help_text='End time of the meeting')
    timezone = TimeZoneField(null=False)
    room = models.CharField(max_length=20, help_text='Room (or other location) for the meeting')

    class Meta:
        ordering = ['weekday']
        #unique_together = (('offering', 'weekday', 'start_time'), ('offering', 'weekday', 'end_time'))

class Role(models.Model):
    """
    Additional roles within the system (not course-related).
    """
    ROLE_CHOICES = (
        ('ADVS', 'Advisor'),
        ('FAC', 'Faculty Member'),
        ('ADMN', 'Departmental Administrator'),
        ('SYSA', 'System Administrator'),
        ('NONE', 'none'),
    )
    ROLES = dict(ROLE_CHOICES)
    person = models.ForeignKey(Person)
    role = models.CharField(max_length=4, choices=ROLE_CHOICES)

    def __unicode__(self):
        return "%s (%s)" % (self.person, self.ROLES[str(self.role)])
    class Meta:
        unique_together = (('person', 'role'),)

