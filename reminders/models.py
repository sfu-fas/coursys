from django.db import models
from django.utils.dates import WEEKDAYS, MONTHS
from courselib.json_fields import JSONField, config_property
from coredata.models import Person, Unit, Semester, Role, Course, CourseOffering, ROLE_CHOICES, ROLES

from courselib.markup import MarkupContentMixin
from autoslug import AutoSlugField
from courselib.slugs import make_slug


REMINDER_TYPE_CHOICES = [
    ('PERS', 'Me personally'),
    ('ROLE', 'All people with role'),
    ('INST', 'Me when teaching a specific course'),
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


class ReminderQuerySet(models.QuerySet):
    pass


class BaseManager(models.Manager):
    def get_queryset(self):
        qs = super(BaseManager, self).get_queryset().filter(status='A')
        return qs
    #def get_queryset(self):
    #    return super().get_queryset()


ReminderManager = BaseManager.from_queryset(ReminderQuerySet)


class Reminder(models.Model):
    reminder_type = models.CharField(max_length=4, choices=REMINDER_TYPE_CHOICES, null=False, blank=False, verbose_name='Who gets reminded?')
    date_type = models.CharField(max_length=4, choices=REMINDER_DATE_CHOICES, null=False, blank=False)
    title = models.CharField(max_length=100, help_text='Title for the reminder/subject for the reminder email')
    content = models.TextField(help_text='Text for the reminder', blank=False)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')

    # for reminder_type == 'PERS': the user who created the reminder.
    person = models.ForeignKey(Person, null=True, on_delete=models.CASCADE)

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
    
    def date_sort(self):
        "Sortable string for date_type etc."
        if self.date_type == 'SEM':
            return 'sem-%02i-%i' % (self.week, int(self.weekday))
        elif self.date_type == 'YEAR':
            return 'year-%02i-%02i' % (int(self.month), self.day)
        
    def date_description(self):
        "Human-readable description of when this reminder fires."
        if self.date_type == 'SEM':
            return 'Each semester: week %i on %s' % (self.week, self.get_weekday_display())
        elif self.date_type == 'YEAR':
            return 'Each year: %s %i' % (self.get_month_display(), self.day)

    def who_description(self):
        "Human-readable description of who gets this reminder."
        if self.reminder_type == 'PERS':
            return 'You personally'
        elif self.reminder_type == 'ROLE':
            return '%s(s) in %s' % (ROLES[self.role], self.unit.label)
        elif self.reminder_type == 'INST':
            return 'You when teaching %s' % (self.course)
        