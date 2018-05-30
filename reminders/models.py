from django.db import models, transaction, IntegrityError
from django.utils.dates import WEEKDAYS, MONTHS
from django.core.mail import send_mail
from django.urls import reverse
from django.conf import settings

from courselib.json_fields import JSONField, config_property
from courselib.branding import product_name
from coredata.models import Person, Unit, Course, Member, Semester, Role, ROLE_CHOICES, ROLES

from autoslug import AutoSlugField
from courselib.slugs import make_slug
from courselib.markup import markup_to_html
import datetime
from string import Template


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

MAX_LATE = 7 # max days late we'll tolerate sending a reminder in the worst case
MESSAGE_EARLY_CREATION = 14 # how many days before the reminder we bother creating the ReminderMessage
HISTORY_RETENTION = 365 # number of days to keep record of ReminderMessages that were sent


REMINDER_HTML_TEMPLATE = Template('''
${content_html}

<p style="font-size: smaller; border-top: 1px solid black;">
You received this message because of a reminder in ${coursys}. It is sent ${when}, to ${who}.
You can <a href="${url}">review this reminder</a> (including editing or deleting it).
</p>
''')


REMINDER_TEXT_TEMPLATE = Template('''${content_text}

--
You received this message because of a reminder in ${coursys}.
It is sent ${when}, to ${who}.
You can review this reminder (including editing or deleting it) here: ${url}
''')


class BaseManager(models.Manager):
    def get_queryset(self):
        qs = super(BaseManager, self).get_queryset().filter(status='A')
        return qs


ReminderManager = BaseManager.from_queryset(models.QuerySet)


class Reminder(models.Model):
    reminder_type = models.CharField(max_length=4, choices=REMINDER_TYPE_CHOICES,
            null=False, blank=False, verbose_name='Who gets reminded?')

    # for reminder_type == 'PERS': the user who created the reminder.
    person = models.ForeignKey(Person, null=False, on_delete=models.CASCADE)

    # for reminder_type == 'ROLE': everyone with a specific role in a specific unit.
    role = models.CharField(max_length=4, null=True, blank=True, choices=ROLE_CHOICES)
    unit = models.ForeignKey(Unit, null=True, blank=True, on_delete=models.CASCADE)

    # for reminder_type == 'INST': an instructor when teaching a specific course.
    course = models.ForeignKey(Course, null=True, blank=True, on_delete=models.CASCADE)
    # also uses .person

    date_type = models.CharField(max_length=4, choices=REMINDER_DATE_CHOICES, null=False, blank=False)

    # for date_type == 'YEAR'
    month = models.CharField(max_length=2, null=True, blank=True, choices=MONTH_CHOICES)
    day = models.PositiveSmallIntegerField(null=True, blank=True)

    # for date_type == 'SEM'
    week = models.PositiveSmallIntegerField(null=True, blank=True)
    weekday = models.CharField(max_length=1, null=True, blank=True, choices=WEEKDAY_CHOICES)

    # used for all reminders
    title = models.CharField(max_length=100, help_text='Title for the reminder/subject for the reminder email')
    content = models.TextField(help_text='Text for the reminder', blank=False, null=False)
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='A', blank=False, null=False)

    def autoslug(self):
        return make_slug(self.reminder_type + '-' + self.date_type + '-' + self.title)
    slug = AutoSlugField(populate_from='autoslug', max_length=50, null=False, editable=False, unique=True)

    config = JSONField(null=False, blank=False, default=dict)  # addition configuration stuff
    # 'markup': markup language used in reminder content: see courselib/markup.py
    # 'math': page uses MathJax? (boolean)
    markup = config_property('markup', 'creole')
    math = config_property('math', False)

    objects = ReminderManager()
    all_objects = models.Manager()

    def _assert_null(self, fields):
        for f in fields:
            assert getattr(self, f) is None

    def _assert_non_null(self, fields):
        for f in fields:
            assert getattr(self, f) is not None

    def save(self, *args, **kwargs):
        # assert reminder_type-related fields are null/nonnull as expected
        if self.reminder_type == 'PERS':
            self._assert_null(['role', 'unit', 'course'])
        elif self.reminder_type == 'ROLE':
            self._assert_null(['course'])
            self._assert_non_null(['role', 'unit'])
        elif self.reminder_type == 'INST':
            self._assert_null(['role', 'unit'])
            self._assert_non_null(['course'])
        else:
            raise ValueError()

        # assert date_type-related fields are null/nonnull as expected
        if self.date_type == 'SEM':
            self._assert_null(['month', 'day'])
            self._assert_non_null(['week', 'weekday'])
        elif self.date_type == 'YEAR':
            self._assert_null(['week', 'weekday'])
            self._assert_non_null(['month', 'day'])
        else:
            raise ValueError()

        res = super().save(*args, **kwargs)

        # destroy any unsent ReminderMessages and recreate to reflect changes.
        with transaction.atomic():
            ReminderMessage.objects.filter(reminder=self, sent=False).delete()
            self.create_reminder_messages(allow_stale=False)

        return res
    
    def __str__(self):
        return 'Reminder(slug=%r, person__userid=%r, title=%r)' % (self.slug, self.person.userid, self.title)

    def get_absolute_url(self):
        return reverse('reminders:view', kwargs={'reminder_slug': self.slug})

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
        
    def when_description(self):
        "Human-readable description of when this reminder fires."
        if self.date_type == 'SEM':
            return 'each semester, week %i on %s' % (self.week, self.get_weekday_display())
        elif self.date_type == 'YEAR':
            return 'each year, %s %i' % (self.get_month_display(), self.day)
        else:
            raise ValueError()

    def who_description(self):
        "Human-readable description of who gets this reminder."
        if self.reminder_type == 'PERS':
            return 'you personally'
        elif self.reminder_type == 'ROLE':
            return '%s(s) in %s' % (ROLES[self.role], self.unit.label)
        elif self.reminder_type == 'INST':
            return 'you when teaching %s' % (self.course)
        else:
            raise ValueError()

    def html_content(self):
        return markup_to_html(self.content, self.markup, restricted=True)

    # ReminderMessage-related functionality

    @staticmethod
    def reminder_message_range(allow_stale=True):
        "Date range where we want to maybe create ReminderMessages."
        today = datetime.date.today()
        if allow_stale:
            start = today - datetime.timedelta(days=MAX_LATE)
        else:
            start = today
        return start, today + datetime.timedelta(days=MESSAGE_EARLY_CREATION)

    def create_reminder_on(self, date, start_date, end_date):
        if start_date > date or date > end_date:
            # not timely, so ignore
            return

        if self.reminder_type == 'ROLE':
            roles = Role.objects_fresh.filter(unit=self.unit, role=self.role).select_related('person')
            recipients = [r.person for r in roles]
        elif self.reminder_type in ['PERS', 'INST']:
            recipients = [self.person]
        else:
            raise ValueError()

        for recip in recipients:
            ident = '%s_%s_%s' % (self.slug, recip.userid_or_emplid(), date.isoformat())
            # ident length: slug (50) + userid/emplid (9) + ISO date (10) + _ (2) <= 71
            rm = ReminderMessage(reminder=self, sent=False, date=date, person=recip, ident=ident)
            with transaction.atomic():
                try:
                    rm.save()
                except IntegrityError:
                    # already been created because we got IntegrityError on rm.ident
                    pass

    def create_reminder_messages(self, start_date=None, end_date=None, allow_stale=True):
        """
        Create any ReminderMessages that don't already exist, between startdate and enddate.

        Idempotent.
        """
        if self.status == 'D':
            return

        if not start_date or not end_date:
            start_date, end_date = self.reminder_message_range(allow_stale=allow_stale)

        if self.date_type == 'YEAR':
            next1 = datetime.date(year=start_date.year, month=int(self.month), day=self.day)
            next2 = datetime.date(year=start_date.year+1, month=int(self.month), day=self.day)
            self.create_reminder_on(next1, start_date, end_date)
            self.create_reminder_on(next2, start_date, end_date)

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
                    next = sem.duedate(self.week, int(self.weekday), time=None)
                    self.create_reminder_on(next, start_date, end_date)

        else:
            raise ValueError()

    @classmethod
    def create_all_reminder_messages(cls):
        """
        Create ReminderMessages for all Reminders.

        Idempotent.
        """
        startdate, enddate = cls.reminder_message_range()
        for r in cls.objects.all(): # can we do better than .all()?
            r.create_reminder_messages(startdate, enddate)


class ReminderMessage(models.Model):
    """
    An instance of a reminder message this needs to be (or has recently been) sent.
    """
    reminder = models.ForeignKey(Reminder, null=False, on_delete=models.CASCADE)
    date = models.DateField(null=False, blank=False)
    sent = models.BooleanField(null=False, default=False)
    sent_at = models.DateTimeField(null=True, blank=True) # actual datetime it was sent
    # reminder recipient
    person = models.ForeignKey(Person, null=False, on_delete=models.CASCADE)
    # identifying string for this reminder message: used to check for duplicates
    ident = models.CharField(max_length=100, blank=False, null=False, db_index=True, unique=True)

    def __str__(self):
        return 'ReminderMessage(ident=%r, reminder__slug=%r, person__userid=%r, date=%r)' % (
            self.ident, self.reminder.slug, self.person.userid, self.date)

    @classmethod
    def send_all(cls):
        """
        Send all messages that are pending and not yet sent.
        """
        today = datetime.date.today()
        rms = cls.objects.filter(sent=False, date__lte=today) \
            .select_related('person', 'reminder', 'reminder__person', 'reminder__course', 'reminder__unit')
        for rm in rms:
            rm.send()

    @classmethod
    def cleanup(cls):
        """
        Purge any old ReminderMessages.
        """
        cutoff = datetime.date.today() - datetime.timedelta(days=HISTORY_RETENTION)
        old_rms = cls.objects.filter(sent=True, date__lt=cutoff)
        old_rms.delete()

    @transaction.atomic
    def send(self):
        """
        Send email for this ReminderMessage
        """
        assert not self.sent

        today = datetime.date.today()
        if self.date < today - datetime.timedelta(days=MAX_LATE):
            raise ValueError('ReminderMessage has not been sent, but is alarmingly past-due.')

        content_html = self.reminder.html_content()
        content_text = self.reminder.content # the creole/markdown is good enough for the plain-text version?

        hint = 'admin' if self.reminder.reminder_type == 'ROLE' else 'other'
        message_context = {
            'content_html': content_html,
            'content_text': content_text,
            'coursys': product_name(hint=hint),
            'when': self.reminder.when_description(),
            'who': self.reminder.who_description(),
            'url': settings.BASE_ABS_URL + self.reminder.get_absolute_url(),
        }

        subject = 'Reminder: ' + self.reminder.title
        message = REMINDER_TEXT_TEMPLATE.substitute(message_context)
        html_message = REMINDER_HTML_TEMPLATE.substitute(message_context)
        from_ = self.reminder.person.full_email()
        to = self.person.full_email()

        send_mail(subject=subject, message=message, html_message=html_message, from_email=from_, recipient_list=[to])

        self.sent_at = datetime.datetime.now()
        self.sent = True
        self.save()
