from django.db import models, IntegrityError
from django.utils.dates import WEEKDAYS, MONTHS
from courselib.json_fields import JSONField, config_property
from coredata.models import Person, Unit, Course, Member, Semester, Role, ROLE_CHOICES, ROLES

from autoslug import AutoSlugField
from courselib.slugs import make_slug
import datetime


REMINDER_TYPE_CHOICES = [
    ('PERS', 'Me personally'),
    ('INST', 'Me when teaching a specific course'),
    ('ROLE', 'All people with role'),
]
#REMINDER_TYPES = dict(REMINDER_TYPE_CHOICES)

REMINDER_DATE_CHOICES = [
    ('YEAR', 'Annually on a month/day'),
    ('SEM', 'Semesterly on a week/weekday'),
]
#REMINDER_DATES = dict(REMINDER_DATE_CHOICES)

STATUS_CHOICES = [
    ('A', 'Active'),
    ('D', 'Deleted'),
]

WEEKDAY_CHOICES = [(str(n), w) for n, w in WEEKDAYS.items()]
MONTH_CHOICES = [(str(n), w) for n, w in MONTHS.items()]


class BaseManager(models.Manager):
    def get_queryset(self):
        qs = super(BaseManager, self).get_queryset().filter(status='A')
        return qs


ReminderManager = BaseManager.from_queryset(models.QuerySet)


class Reminder(models.Model):
    reminder_type = models.CharField(max_length=4, choices=REMINDER_TYPE_CHOICES, null=False, blank=False, verbose_name='Who gets reminded?')
    date_type = models.CharField(max_length=4, choices=REMINDER_DATE_CHOICES, null=False, blank=False)
    title = models.CharField(max_length=100, help_text='Title for the reminder/subject for the reminder email')
    content = models.TextField(help_text='Text for the reminder', blank=False, null=False)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A', blank=False, null=False)

    # for reminder_type == 'PERS': the user who created the reminder.
    person = models.ForeignKey(Person, null=False, on_delete=models.CASCADE)

    # for reminder_type == 'ROLE': everyone with a specific role in a specific unit.
    role = models.CharField(max_length=4, null=True, blank=True, choices=ROLE_CHOICES)
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.CASCADE)

    # for reminder_type == 'INST': an instructor when teaching a specific course.
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.CASCADE)
    # also uses .person

    # for date_type == 'YEAR'
    month = models.CharField(max_length=1, null=True, blank=True, choices=MONTH_CHOICES)
    day = models.PositiveSmallIntegerField(null=True, blank=True)

    # for date_type == 'SEM'
    week = models.PositiveSmallIntegerField(null=True, blank=True)
    weekday = models.CharField(max_length=1, null=True, blank=True, choices=WEEKDAY_CHOICES)
    
    def autoslug(self):
        return make_slug(self.reminder_type + '-' + self.date_type + '-' + self.title)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff
    # 'markup': markup language used in reminder content: see courselib/markup.py
    # 'math': page uses MathJax? (boolean)
    markup = config_property('markup', 'creole')
    math = config_property('math', False)

    objects = ReminderManager()
    all_objects = models.Manager()

    def save(self, *args, **kwargs):
        # TODO assert coherence of the reminder type and other fields
        return super().save(*args, **kwargs)
    
    def __str__(self):
        return 'Reminder(slug=%r, person__userid=%r, title=%r)' % (self.slug, self.person.userid, self.title)

    def can_be_accessed_by(self, person):
        "Can this person read & edit this reminder?"
        if self.reminder_type in ['PERS', 'INST']:
            return self.person == person
        elif self.reminder_type == 'ROLE':
            roles = Role.objects.filter(role=self.role, unit=self.unit).select_related('person')
            people = {r.person for r in roles}
            return person in people
        else:
            raise ValueError()

    @staticmethod
    def relevant_courses(person):
        cutoff = datetime.date.today() - datetime.timedelta(days=365)
        instructors = Member.objects.filter(role='INST', person=person, offering__semester__end__gt=cutoff).select_related(
            'offering__course')
        return {m.offering.course for m in instructors}

    def date_sort(self):
        "Sortable string for date_type etc."
        if self.date_type == 'SEM':
            return 'sem-%02i-%i' % (self.week, int(self.weekday))
        elif self.date_type == 'YEAR':
            return 'year-%02i-%02i' % (int(self.month), self.day)
        else:
            raise ValueError()
        
    def date_description(self):
        "Human-readable description of when this reminder fires."
        if self.date_type == 'SEM':
            return 'Each semester: week %i on %s' % (self.week, self.get_weekday_display())
        elif self.date_type == 'YEAR':
            return 'Each year: %s %i' % (self.get_month_display(), self.day)
        else:
            raise ValueError()

    def who_description(self):
        "Human-readable description of who gets this reminder."
        if self.reminder_type == 'PERS':
            return 'You personally'
        elif self.reminder_type == 'ROLE':
            return '%s(s) in %s' % (ROLES[self.role], self.unit.label)
        elif self.reminder_type == 'INST':
            return 'You when teaching %s' % (self.course)
        else:
            raise ValueError()

    # ReminderMessage-related functionality

    @staticmethod
    def reminder_message_range():
        "Date range where we want to maybe create ReminderMessages."
        today = datetime.date.today()
        # TODO: this is a pretty unrealistic range
        return today - datetime.timedelta(days=365), today + datetime.timedelta(days=365)

    def create_reminder_on(self, date, startdate, enddate):
        if startdate > date or date > enddate:
            # not timely, so ignore
            return

        # TODO: not self.person, but forall relevant people
        recip = self.person
        ident = '%s_%s_%s' % (self.slug, recip.userid_or_emplid(), date.isoformat())
        rm = ReminderMessage(reminder=self, sent=False, date=date, person=recip, ident=ident)
        print(rm)
        try:
            rm.save()
        except IntegrityError:
            # already been created because we got IntegrityError on rm.ident
            pass

    def create_reminder_messages(self, startdate, enddate):
        """
        Create any ReminderMessages that don't already exist, between startdate and enddate.
        """
        if self.date_type == 'YEAR':
            next1 = datetime.date(year=startdate.year, month=int(self.month), day=self.day)
            next2 = datetime.date(year=startdate.year+1, month=int(self.month), day=self.day)
            self.create_reminder_on(next1, startdate, enddate)
            self.create_reminder_on(next2, startdate, enddate)
        elif self.date_type == 'SEM':
            if self.reminder_type == 'INST':
                # limit to semesters actually teaching
                instructors = Member.objects.filter(role='INST', person=self.person, offering__course=self.course) \
                    .exclude(offering__component='CAN').select_related('offering__course')
                semesters = {m.offering.semester for m in instructors}
            else:
                semesters = None

            this_sem = Semester.current()
            for sem in [this_sem.previous_semester(), this_sem, this_sem.next_semester()]:
                if semesters is None or sem in semesters:
                    next = sem.duedate(self.week, int(self.weekday), datetime.time()).date()
                    self.create_reminder_on(next, startdate, enddate)
        else:
            raise ValueError()

    @classmethod
    def create_all_reminder_messages(cls):
        """
        Create ReminderMessages for all Reminders.
        """
        startdate, enddate = Reminder.reminder_message_range()
        for r in Reminder.objects.all():
            r.create_reminder_messages(startdate, enddate)


class ReminderMessage(models.Model):
    """
    An instance of a reminder message this needs to be (or has been) sent.
    """
    reminder = models.ForeignKey(Reminder, null=False, on_delete=models.CASCADE)
    sent = models.BooleanField(null=False, default=False)
    date = models.DateField(null=False, blank=False)
    # reminder recipient
    person = models.ForeignKey(Person, null=False, on_delete=models.CASCADE)
    # identifying string for this reminder message: used to check for duplicates
    ident = models.CharField(max_length=255, blank=False, null=False, db_index=True, unique=True)

    def __str__(self):
        return 'ReminderMessage(ident=%r, reminder__slug=%r, person__userid=%r, date=%r)' % (
            self.ident, self.reminder.slug, self.person.userid, self.date)

