from django.db import models
from courselib.json_fields import JSONField, config_property
from coredata.models import Person, Unit, Semester, Role, Course, CourseOffering, ROLE_CHOICES
from courselib.markup import MarkupContentMixin


REMINDER_TYPE_CHOICES = [
    ('PERS', 'A single person'),
    ('ROLE', 'All people with role'),
    ('INST', 'A person when teaching a specific course'),
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


class ReminderQuerySet(models.QuerySet):
    pass

class BaseManager(models.Manager):
    def get_queryset(self):
        qs = super(BaseManager, self).get_queryset().filter(active='A')
        return qs    def get_queryset(self):
        return super().get_queryset()


CustomManager = BaseManager.from_queryset(ReminderQuerySet)


class Reminder(models.Model):
    reminder_type = models.CharField(max_length=4, choices=REMINDER_TYPE_CHOICES)
    date_type = models.CharField(max_length=4, choices=REMINDER_DATE_CHOICES)
    content = models.TextField(help_text='Text for the reminder')
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A')

    # for reminder_type == 'PERS': the user who created the reminder.
    person = models.ForeignKey(Person, null=True, on_delete=models.CASCADE)

    # for reminder_type == 'ROLE': everyone with a specific role in a specific unit.
    role = models.CharField(max_length=4, null=True, choices=ROLE_CHOICES)
    unit = models.ForeignKey(Unit, null=True, on_delete=models.CASCADE)

    # for reminder_type == 'INST': an instructor when teaching a specific course.
    course = models.ForeignKey(Course, null=True, on_delete=models.CASCADE)
    # also uses .person

    # for date_type == 'YEAR'
    month = models.PositiveSmallIntegerField(null=True)
    day = models.PositiveSmallIntegerField(null=True)

    # for date_type == 'SEM'
    week = models.PositiveSmallIntegerField(null=True)
    weekday = models.PositiveSmallIntegerField(null=True)

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