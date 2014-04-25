from decimal import Decimal, InvalidOperation
import datetime
import csv
import os
import re

from django.db import models
from django.db.models import Q
from django.core.urlresolvers import reverse

from autoslug import AutoSlugField
from bitfield import BitField
from jsonfield import JSONField

from coredata.models import Unit, Person, Semester
from courselib.json_fields import config_property
from courselib.slugs import make_slug
from courselib.text import normalize_newlines, many_newlines
from cache_utils.decorators import cached

from faculty.event_types.awards import FellowshipEventHandler
from faculty.event_types.awards import GrantApplicationEventHandler
from faculty.event_types.awards import AwardEventHandler
from faculty.event_types.awards import TeachingCreditEventHandler
from faculty.event_types.career import AppointmentEventHandler
from faculty.event_types.career import OnLeaveEventHandler
from faculty.event_types.career import SalaryBaseEventHandler
from faculty.event_types.career import SalaryModificationEventHandler
from faculty.event_types.career import TenureApplicationEventHandler
from faculty.event_types.career import TenureReceivedEventHandler
from faculty.event_types.career import StudyLeaveEventHandler
from faculty.event_types.career import AccreditationFlagEventHandler
from faculty.event_types.constants import EVENT_FLAGS
from faculty.event_types.info import CommitteeMemberHandler
from faculty.event_types.info import ExternalAffiliationHandler
from faculty.event_types.info import ExternalServiceHandler
from faculty.event_types.info import OtherEventHandler
from faculty.event_types.info import ResearchMembershipHandler
from faculty.event_types.info import SpecialDealHandler
from faculty.event_types.position import AdminPositionEventHandler
from faculty.event_types.teaching import NormalTeachingLoadHandler
from faculty.event_types.teaching import OneInNineHandler
from faculty.util import ReportingSemester

# CareerEvent.event_type value -> CareerEventManager class
HANDLERS = [
    AdminPositionEventHandler,
    AppointmentEventHandler,
    AwardEventHandler,
    CommitteeMemberHandler,
    ExternalAffiliationHandler,
    ExternalServiceHandler,
    FellowshipEventHandler,
    GrantApplicationEventHandler,
    NormalTeachingLoadHandler,
    OnLeaveEventHandler,
    OneInNineHandler,
    OtherEventHandler,
    ResearchMembershipHandler,
    SalaryBaseEventHandler,
    SalaryModificationEventHandler,
    SpecialDealHandler,
    StudyLeaveEventHandler,
    TeachingCreditEventHandler,
    TenureApplicationEventHandler,
    TenureReceivedEventHandler,
    AccreditationFlagEventHandler,
]
EVENT_TYPES = {handler.EVENT_TYPE: handler for handler in HANDLERS}
EVENT_TYPE_CHOICES = [(handler.EVENT_TYPE, handler) for handler in HANDLERS]

EVENT_TAGS = {
                'title': '"Mr", "Miss", etc.',
                'first_name': 'recipient\'s first name',
                'last_name': 'recipients\'s last name',
                'his_her' : '"his" or "her" (or use His_Her for capitalized)',
                'he_she' : '"he" or "she" (or use He_She for capitalized)',
                'start_date': 'start date of the event, if applicable',
                'end_date': 'end date of the event, if applicable',
                'event_title': 'name of event',
                'current_rank': "faculty member's current rank",
            }

#event specific tags
ADD_TAGS = {
                'position': 'type of position',
                'teaching_credit': 'teaching credit adjustment per semester for this event',
                'spousal_hire': 'yes/no',
                'leaving_reason': 'reason for leaving',
                'award': 'recipient\'s reward',
                'awarded_by': 'entity that has issued the award',
                'amount': 'dollar amount',
                'externally_funded': 'yes/no - external to SFU?',
                'in_payroll': 'yes/no - internal to SFU?',
                'committee_unit': 'committee faculty',
                'org_name': 'name of the organization',
                'org_type': 'type of organization sfu/academic/private',
                'org_class': 'classification external/not-for-profit',
                'is_research': 'yes/no - research institute?',
                'is_adjunct': 'yes/no - adjunct?',
                'grant_name': 'name of the grant',
                'load': 'teaching load',
                'leave_fraction': 'Fraction of salary received during leave eg. "2/3"',
                'teaching_load_decrease': 'per semester descrease in teaching load eg. "1/3"',
                'step': 'current salary step',
                'report_received': 'yes/no - report received?',
                'credits': 'teaching credit adjustment per semester',
                'teaching_credits': 'teaching credit per semester associated with this event',
                'category': 'eg. buyout/release/other',
            }

# adapted from https://djangosnippets.org/snippets/562/
class CareerQuerySet(models.query.QuerySet):
    def not_deleted(self):
        """
        All Career Events that have not been deleted.
        """
        return self.exclude(status='D')

    def approved(self):
        """
        All Career Events that have not been deleted.
        """
        return self.filter(status='A')

    def effective_now(self):
        return self.effective_date(datetime.date.today())

    def effective_date(self, date):
        end_okay = Q(end_date__isnull=True) | Q(end_date__gte=date)
        return self.exclude(status='D').filter(start_date__lte=date).filter(end_okay)

    def effective_semester(self, semester):
        """
        Returns CareerEvents starting and ending within this semester.
        """
        if isinstance(semester, Semester):
            semester = ReportingSemester(semester)

        start = semester.start_date
        end = semester.end_date

        end_okay = Q(end_date__isnull=True) | Q(end_date__lte=end) & Q(end_date__gte=start)
        return self.exclude(status='D').filter(start_date__gte=start).filter(end_okay)

    def overlaps_semester(self, semester):
        """
        Returns CareerEvents occurring during the semester.
        """
        if isinstance(semester, Semester):
            semester = ReportingSemester(semester)

        start = semester.start_date
        end = semester.end_date

        end_okay = Q(end_date__isnull=True) | Q(end_date__gte=start)
        return self.exclude(status='D').filter(start_date__lte=end).filter(end_okay)

    def within_daterange(self, start, end, inclusive=True):
        if not inclusive:
            filters = {"start_date__gt": start, "end_date__lt": end}
        else:
            filters = {"start_date__gte": start, "end_date__lte": end}
        return self.exclude(status='D').filter(**filters)

    def overlaps_daterange(self, start, end):
        """
        Returns CareerEvents occurring during the date range.
        """
        end_okay = Q(end_date__isnull=True) | Q(end_date__gte=start)
        return self.exclude(status='D').filter(start_date__lte=end).filter(end_okay)

    def by_type(self, Handler):
        """
        Returns all CareerEvents matching the given CareerEventHandler class.
        """
        return self.filter(event_type__exact=Handler.EVENT_TYPE)

    def only_units(self, units):
        return self.filter(unit__in=units)

    def only_subunits(self, units):
        subunit_ids = Unit.sub_unit_ids(units)
        return self.filter(unit__id__in=subunit_ids)


# adapted from https://djangosnippets.org/snippets/562/
class CareerEventManager(models.Manager):
    def get_query_set(self):
        model = models.get_model('faculty', 'CareerEvent')
        return CareerQuerySet(model)

    def __getattr__(self, attr, *args):
        try:
            return getattr(self.__class__, attr, *args)
        except AttributeError:
            return getattr(self.get_query_set(), attr, *args)


class CareerEvent(models.Model):
    STATUS_CHOICES = (
        ('NA', 'Needs Approval'),
        ('A', 'Approved'),
        ('D', 'Deleted'),
    )

    person = models.ForeignKey(Person, related_name="career_events")
    unit = models.ForeignKey(Unit)

    slug = AutoSlugField(populate_from='slug_string', unique_with=('person', 'unit'),
                         slugify=make_slug, null=False, editable=False)
    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=True, blank=True)
    comments = models.TextField(blank=True)

    event_type = models.CharField(max_length=10, choices=EVENT_TYPE_CHOICES)
    config = JSONField(default={})

    flags = BitField(flags=EVENT_FLAGS, default=0)

    status = models.CharField(max_length=2, choices=STATUS_CHOICES, blank=False, default='')
    import_key = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CareerEventManager()

    class Meta:
        ordering = (
            '-start_date',
            '-end_date',
            'event_type',
        )

    def __unicode__(self):
        return u"%s from %s to %s" % (self.get_event_type_display(), self.start_date, self.end_date)

    def save(self, editor, call_from_handler=False, *args, **kwargs):
        # we're doing to so we can add an audit trail later.
        assert editor.__class__.__name__ == 'Person'
        assert call_from_handler, "must save through handler"
        return super(CareerEvent, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("faculty_event_view", args=[self.person.userid, self.slug])

    def get_status_change_url(self):
        return reverse("faculty_change_event_status", args=[self.person.userid, self.slug])

    def get_change_url(self):
        return reverse("faculty_change_event", args=[self.person.userid, self.slug])

    @property
    def slug_string(self):
        return u'{} {}'.format(self.start_date.year, self.get_event_type_display())

    @classmethod
    @cached(24*3600)
    def current_ranks(cls, person):
        """
        Return a string representing the current rank(s) for this person
        """
        salaries = CareerEvent.objects.filter(person=person, event_type='SALARY').effective_now()
        if not salaries:
            return 'unknown'

        ranks = set(s.get_handler().get_rank_display() for s in salaries)
        return ', '.join(ranks)

    def get_event_type_display(self):
        "Override to display nicely"
        return EVENT_TYPES[self.event_type].NAME

    def get_handler(self):
        if not hasattr(self, 'handler_cache'):
            self.handler_cache = EVENT_TYPES[self.event_type](self)
        return self.handler_cache

    def get_duration_within_range(self, start, end):
        """
        Returns the number of days the event overlaps with a given date range
        """
        if (self.start_date < end and (self.end_date == None or self.end_date > start)):
            s = max(start, self.start_date)
            if self.end_date:
                e = min(end, self.end_date)
            else:
                e = end
            delta = e - s
            return delta.days
        return 0

    def filter_classes(self):
        """
        return the class="..." value for this event on the summary page (for filtering)
        """
        today = datetime.date.today()
        classes = []
        #if self.start_date <= today and (self.end_date == None or self.end_date >= today):
        if self.end_date == None or self.end_date >= today:
            classes.append('current')
        if self.flags.affects_teaching:
            classes.append('teach')
        if self.flags.affects_salary:
            classes.append('salary')

        return ' '.join(classes)

    def memo_info(self):
        """
        Context dictionary for building memo text
        """

        # basic personal stuff
        gender = self.person.gender()
        title = self.person.get_title()

        if gender == "M" :
            hisher = "his"
            heshe = 'he'
        elif gender == "F":
            hisher = "her"
            heshe = 'she'
        else:
            hisher = "his/her"
            heshe = 'he/she'

        # grab event type specific config data
        handler = self.get_handler()
        config_data = self.config
        for key in config_data:
            try:
                config_data[key] = unicode(handler.get_display(key))
            except AttributeError:
                pass

        start = self.start_date.strftime('%B %d, %Y')
        end = self.end_date.strftime('%B %d, %Y') if self.end_date else '???'

        ls = { # if changing, also update EVENT_TAGS above!
               # For security reasons, all values must be strings (to avoid presenting dangerous methods in templates)
                'title' : title,
                'his_her' : hisher,
                'His_Her' : hisher.title(),
                'he_she' : heshe,
                'He_She' : heshe.title(),
                'first_name': self.person.first_name,
                'last_name': self.person.last_name,
                'start_date': start,
                'end_date': end,
                'current_rank': CareerEvent.current_ranks(self.person)
              }
        ls = dict(ls.items() + config_data.items())
        return ls



from django.conf import settings
from django.core.files.storage import FileSystemStorage
NoteSystemStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)
def attachment_upload_to(instance, filename):
    """
    callback to avoid path in the filename(that we have append folder structure to) being striped
    """
    fullpath = os.path.join(
        'faculty',
        instance.career_event.person.userid_or_emplid(),
        instance.career_event.slug,
        datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
        filename.encode('ascii', 'ignore'))
    return fullpath


class DocumentAttachment(models.Model):
    """
    Document attached to a CareerEvent.
    """
    career_event = models.ForeignKey(CareerEvent, null=False, blank=False, related_name="attachments")
    title = models.CharField(max_length=250, null=False)
    slug = AutoSlugField(populate_from='title', null=False, editable=False, unique_with=('career_event',))
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, help_text='Document attachment created by.')
    contents = models.FileField(storage=NoteSystemStorage, upload_to=attachment_upload_to)
    mediatype = models.CharField(max_length=200, null=True, blank=True, editable=False)

    def __unicode__(self):
        return self.contents.filename

    class Meta:
        ordering = ("created_at",)
        unique_together = (("career_event", "slug"),)

    def contents_filename(self):
        return os.path.basename(self.contents.name)


class MemoTemplate(models.Model):
    """
    A template for memos.
    """
    unit = models.ForeignKey(Unit, null=False, blank=False)
    label = models.CharField(max_length=250, null=False, verbose_name='Template Name',
                             help_text='The name for this template (that you select it by when using it)')
    event_type = models.CharField(max_length=10, null=False, choices=EVENT_TYPE_CHOICES,
                                  help_text='The type of event that this memo applies to')
    default_from = models.CharField(verbose_name='Default From', help_text='The default sender of the memo', max_length=255, blank=True)
    subject = models.CharField(verbose_name='Default Subject', help_text='The default subject of the memo', max_length=255)
    template_text = models.TextField(help_text="The template for the memo. It may be edited when creating "
            "each memo. (i.e. 'Congratulations {{first_name}} on ... ')")

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, help_text='Memo template created by.', related_name='+')
    hidden = models.BooleanField(default=False)

    def autoslug(self):
        return make_slug(self.unit.label + "-" + self.label)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)

    def __unicode__(self):
        return u"%s in %s" % (self.label, self.unit)

    class Meta:
        unique_together = ('unit', 'label')

    def save(self, *args, **kwargs):
        self.template_text = normalize_newlines(self.template_text.rstrip())
        super(MemoTemplate, self).save(*args, **kwargs)

    def get_event_type_display(self):
        "Override to display nicely"
        return EVENT_TYPES[self.event_type].NAME


class Memo(models.Model):
    """
    A memo created by the system, and attached to a CareerEvent.
    """
    career_event = models.ForeignKey(CareerEvent, null=False, blank=False)
    unit = models.ForeignKey(Unit, null=False, blank=False, help_text="The unit producing the memo: will determine the letterhead used for the memo.")

    sent_date = models.DateField(default=datetime.date.today, help_text="The sending date of the letter")
    to_lines = models.TextField(verbose_name='Attention', help_text='Recipient of the memo', null=True, blank=True)
    cc_lines = models.TextField(verbose_name='CC lines', help_text='Additional recipients of the memo', null=True, blank=True)
    from_person = models.ForeignKey(Person, null=True, related_name='+')
    from_lines = models.TextField(verbose_name='From', help_text='Name (and title) of the sender, e.g. "John Smith, Applied Sciences, Dean"')
    subject = models.TextField(help_text='The subject of the memo (lines will be formatted separately in the memo header)')

    template = models.ForeignKey(MemoTemplate, null=True)
    memo_text = models.TextField(help_text="I.e. 'Congratulations on ... '")
    #salutation = models.CharField(max_length=100, default="To whom it may concern", blank=True)
    #closing = models.CharField(max_length=100, default="Sincerely")

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, help_text='Letter generation requested by.', related_name='+')
    hidden = models.BooleanField(default=False)
    config = JSONField(default={})  # addition configuration for within the memo
    # XXX: 'use_sig': use the from_person's signature if it exists?
    #                 (Users set False when a real legal signature is required.

    use_sig = config_property('use_sig', default=True)

    def autoslug(self):
        return make_slug(self.career_event.slug + "-" + self.template.label)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique_with=('career_event',))

    def __unicode__(self):
        return u"%s memo for %s" % (self.template.label, self.career_event)

    def save(self, *args, **kwargs):
        # normalize text so it's easy to work with
        if not self.to_lines:
            self.to_lines = ''
        self.to_lines = normalize_newlines(self.to_lines.rstrip())
        self.from_lines = normalize_newlines(self.from_lines.rstrip())
        self.subject = normalize_newlines(self.subject.rstrip())
        self.memo_text = normalize_newlines(self.memo_text.rstrip())
        self.memo_text = many_newlines.sub('\n\n', self.memo_text)
        super(Memo, self).save(*args, **kwargs)

    def write_pdf(self, response):
        from dashboard.letters import OfficialLetter, MemoContents
        doc = OfficialLetter(response, unit=self.unit)
        l = MemoContents(to_addr_lines=self.to_lines.split("\n"),
                        from_name_lines=self.from_lines.split("\n"),
                        date=self.sent_date,
                        subject=self.subject.split("\n"),
                        cc_lines=self.cc_lines.split("\n"),
                        )
        content_lines = self.memo_text.split("\n\n")
        l.add_paragraphs(content_lines)
        doc.add_letter(l)
        doc.write()

class EventConfig(models.Model):
    """
    A unit's configuration for a particular event type
    """
    unit = models.ForeignKey(Unit, null=False, blank=False)
    event_type = models.CharField(max_length=10, null=False, choices=EVENT_TYPE_CHOICES)
    config = JSONField(default={})

    class Meta:
        unique_together = ('unit', 'event_type')


class TempGrantManager(models.Manager):
    def create_from_csv(self, fh, creator):
        reader = csv.reader(fh.read().splitlines())
        # TODO: do we have a csv file to play with, or should we use the XLS greg gave us?
        failed = []
        created = []
        for row in reader:
            try:
                fund = unicode(row[0].strip(), errors='ignore')
            except IndexError:
                continue
            if re.match('[0-9]{2} ?-? ?[0-9]{6}$', fund):
                try:
                    label = unicode(row[1].strip(), errors='ignore')
                except IndexError:
                    failed.append(row)
                    continue
                try:
                    # Grab things from the CSV
                    balance = Decimal(unicode(row[4].strip(), errors='ignore'))
                    cur_month = Decimal(unicode(row[5].strip(), errors='ignore'))
                    ytd_actual = Decimal(unicode(row[6].strip(), errors='ignore'))
                    cur_balance = Decimal(unicode(row[8].strip(), errors='ignore'))
                except (IndexError, InvalidOperation):
                    failed.append(row)
                    continue

                # If Grant with the label already exists, then we update the balance
                try:
                    grant = Grant.objects.get(label__exact=label)
                except Grant.DoesNotExist:
                    pass
                else:
                    gb = grant.update_balance(cur_balance, cur_month, ytd_actual)

                # Make sure its not a duplicate label for Temp Grants
                if not TempGrant.objects.filter(label__exact=label).exists():
                    t = TempGrant(
                        label=label,
                        initial=balance,
                        project_code=fund,
                        creator=creator,
                        config={"cur_month": cur_month,
                                "ytd_actual": ytd_actual,
                                "cur_balance": cur_balance}
                    )
                    t.save()
                    created.append(t)
        return created, failed


class TempGrant(models.Model):
    label = models.CharField(max_length=255, help_text="for identification from FAST import", unique=True)
    initial = models.DecimalField(verbose_name="initial balance", max_digits=12, decimal_places=2)
    project_code = models.CharField(max_length=32, help_text="The fund and project code, like '13-123456'")
    import_key = models.CharField(null=True, blank=True, max_length=255, help_text="e.g. 'nserc-43517b4fd422423382baab1e916e7f63'")
    creator = models.ForeignKey(Person, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    config = JSONField(default={}) # addition configuration for within the temp grant

    objects = TempGrantManager()

    def get_convert_url(self):
        return reverse("convert_grant", args=[self.id])

    def get_delete_url(self):
        return reverse("delete_grant", args=[self.id])

    def grant_dict(self, **kwargs):
        data = {
            "label": self.label,
            "title": self.label,
            "project_code": self.project_code,
            "initial": self.initial,
            "import_key": self.import_key,
        }
        data.update(**kwargs)
        return data


class GrantManager(models.Manager):
    def active(self):
        qs = self.get_query_set()
        return qs.filter(status='A')


class Grant(models.Model):
    STATUS_CHOICES = (
        ("A", "Active"),
        ("D", "Deleted"),
    )
    title = models.CharField(max_length=64, help_text='Label for the grant within this system')
    slug = AutoSlugField(populate_from='title', unique_with=("unit",), null=False, editable=False)
    label = models.CharField(max_length=255, help_text="for identification from FAST import", unique=True, db_index=True)
    owners = models.ManyToManyField(Person, through='GrantOwner', blank=False, null=True, help_text='Who owns/controls this grant?')
    project_code = models.CharField(max_length=32, db_index=True, help_text="The fund and project code, like '13-123456'")
    start_date = models.DateField(null=False, blank=False)
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default='A')
    initial = models.DecimalField(verbose_name="Initial balance", max_digits=12, decimal_places=2)
    overhead = models.DecimalField(verbose_name="Annual overhead", max_digits=12, decimal_places=2, help_text="Annual overhead returned to Faculty budget")
    import_key = models.CharField(null=True, blank=True, max_length=255, help_text="e.g. 'nserc-43517b4fd422423382baab1e916e7f63'")
    unit = models.ForeignKey(Unit, null=False, blank=False, help_text="Unit who owns the grant")
    config = JSONField(blank=True, null=True, default={})  # addition configuration for within the grant

    objects = GrantManager()

    def __unicode__(self):
        return u"%s" % self.title

    def get_absolute_url(self):
        return reverse("view_grant", kwargs={'unit_slug': self.unit.slug, 'grant_slug': self.slug})

    def update_balance(self, balance, spent_this_month, actual, date=datetime.datetime.today()):
        gb = GrantBalance.objects.create(
            date=date,
            grant=self,
            balance=balance,
            actual=actual,
            month=spent_this_month
        )
        return gb

class GrantOwner(models.Model):
    grant = models.ForeignKey(Grant)
    person = models.ForeignKey(Person)
    config = JSONField(blank=True, null=True, default={})  # addition configuration

class GrantBalance(models.Model):
    date = models.DateField(default=datetime.date.today)
    grant = models.ForeignKey(Grant, null=False, blank=False)
    balance = models.DecimalField(verbose_name="grant balance", max_digits=12, decimal_places=2)
    actual = models.DecimalField(verbose_name="YTD actual", max_digits=12, decimal_places=2)
    month = models.DecimalField(verbose_name="current month", max_digits=12, decimal_places=2)
    config = JSONField(blank=True, null=True, default={})  # addition configuration within the memo

    def __unicode__(self):
        return u"%s balance as of %s" % (self.grant, self.date)


class FacultyMemberInfo(models.Model):
    person = models.ForeignKey(Person, unique=True, related_name='+')
    title = models.CharField(max_length=50)
    birthday = models.DateField(verbose_name="Birthdate", null=True, blank=True)
    office_number = models.CharField('Office', max_length=20, null=True, blank=True)
    phone_number = models.CharField('Local Phone Number', max_length=20, null=True, blank=True)
    emergency_contact = models.TextField('Emergency Contact Information', blank=True)
    config = JSONField(blank=True, null=True, default={})  # addition configuration

    last_updated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return u'<FacultyMemberInfo({})>'.format(self.person)

    def get_absolute_url(self):
        return reverse('faculty.views.faculty_member_info',
                       args=[self.person.userid_or_emplid()])
