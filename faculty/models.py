from decimal import Decimal, InvalidOperation
import datetime
import csv
import os
import re
import copy
import uuid

from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.apps.registry import apps
from django.utils import timezone

from autoslug import AutoSlugField
from bitfield import BitField
from courselib.json_fields import JSONField

from coredata.models import Unit, Person, Semester, Role, AnyPerson
from courselib.json_fields import config_property
from courselib.slugs import make_slug
from courselib.text import normalize_newlines, many_newlines
from courselib.storage import UploadedFileStorage, upload_path
from cache_utils.decorators import cached

from faculty.event_types.constants import EVENT_FLAGS
from faculty.event_types.awards import FellowshipEventHandler
from faculty.event_types.awards import GrantApplicationEventHandler
from faculty.event_types.awards import AwardEventHandler
from faculty.event_types.awards import TeachingCreditEventHandler
from faculty.event_types.career import AppointmentEventHandler
from faculty.event_types.career import OnLeaveEventHandler
from faculty.event_types.career import SalaryBaseEventHandler
from faculty.event_types.career import SalaryModificationEventHandler
from faculty.event_types.career import TenureApplicationEventHandler
from faculty.event_types.career import StudyLeaveEventHandler
from faculty.event_types.career import AccreditationFlagEventHandler
from faculty.event_types.career import PromotionApplicationEventHandler
from faculty.event_types.career import SalaryReviewEventHandler
from faculty.event_types.career import ContractReviewEventHandler
from faculty.event_types.info import CommitteeMemberHandler
from faculty.event_types.info import ExternalAffiliationHandler
from faculty.event_types.info import ExternalServiceHandler
from faculty.event_types.info import OtherEventHandler
from faculty.event_types.info import ResearchMembershipHandler
from faculty.event_types.info import SpecialDealHandler
from faculty.event_types.info import ResumeEventHandler
from faculty.event_types.position import AdminPositionEventHandler
from faculty.event_types.teaching import NormalTeachingLoadHandler
from faculty.event_types.teaching import OneInNineHandler
from faculty.util import ReportingSemester
from faculty.event_types.career import RANK_CHOICES
from fractions import Fraction

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
    AccreditationFlagEventHandler,
    PromotionApplicationEventHandler,
    SalaryReviewEventHandler,
    ContractReviewEventHandler,
    ResumeEventHandler
]
EVENT_TYPES = {handler.EVENT_TYPE: handler for handler in HANDLERS}
EVENT_TYPE_CHOICES = [(handler.EVENT_TYPE, handler) for handler in HANDLERS]

EVENT_TAGS = {
                'title': '"Mr", "Miss", etc.',
                'first_name': 'recipient\'s first name',
                'last_name': 'recipients\'s last name',
                'his_her' : '"his" or "her" (or use His_Her for capitalized)',
                'he_she' : '"he" or "she" (or use He_She for capitalized)',
                'him_her' : '"him" or "her" (or use Him_Her for capitalized)',
                'start_date': 'start date of the event, if applicable',
                'end_date': 'end date of the event, if applicable',
                'event_title': 'name of event',
                'current_rank': "faculty member's current rank",
                'current_base_salary': "faculty member's current base salary",
                'current_market_diff': "faculty member's current market differential",
                'unit': "unit of which this person is a member",
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


# faculty roles last ~forever, but Role.expiry isn't really checked for them anyway.
FACULTY_ROLE_EXPIRY = datetime.date.today() + datetime.timedelta(days = 100*365)


class CareerQuerySet(models.QuerySet):
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


class CareerEvent(models.Model):
    STATUS_CHOICES = (
        ('NA', 'Needs Approval'),
        ('A', 'Approved'),
        ('D', 'Deleted'),
    )

    person = models.ForeignKey(Person, related_name="career_events", on_delete=models.PROTECT)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)

    slug = AutoSlugField(populate_from='slug_string', unique_with=('person',),
                         slugify=make_slug, null=False, editable=False)
    start_date = models.DateField(null=False, blank=False)
    end_date = models.DateField(null=True, blank=True)
    comments = models.TextField(blank=True)

    event_type = models.CharField(max_length=10, choices=EVENT_TYPE_CHOICES)
    config = JSONField(default=dict)

    flags = BitField(flags=EVENT_FLAGS, default=0)

    status = models.CharField(max_length=2, choices=STATUS_CHOICES, blank=False, default='')
    import_key = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = CareerQuerySet.as_manager()

    class Meta:
        ordering = (
            '-start_date',
            '-end_date',
            'event_type',
        )
        unique_together = (("person", "slug"),)

    def __str__(self):
        return "%s from %s to %s" % (self.get_event_type_display(), self.start_date, self.end_date)

    def save(self, editor, call_from_handler=False, *args, **kwargs):
        # we're doing to so we can add an audit trail later.
        assert editor.__class__.__name__ == 'Person'
        assert call_from_handler, "must save through handler"
        return super(CareerEvent, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("faculty:view_event", args=[self.person.userid, self.slug])

    def get_status_change_url(self):
        return reverse("faculty:change_event_status", args=[self.person.userid, self.slug])

    def get_change_url(self):
        return reverse("faculty:change_event", args=[self.person.userid, self.slug])

    @property
    def slug_string(self):
        return '{} {}'.format(self.start_date.year, self.get_event_type_display())

    def handler_type_name(self):
        return self.get_handler().NAME

    @classmethod
    @cached(6*3600)
    def current_ranks(cls, person_id):
        """
        Return a string representing the current rank(s) for this person
        """
        salaries = CareerEvent.objects.filter(person__id=person_id, event_type='SALARY').effective_now()
        if not salaries:
            return 'unknown'

        ranks = set(s.get_handler().get_rank_display() for s in salaries)
        return ', '.join(ranks)

    @classmethod
    @cached(6 * 3600)
    def ranks_as_of_semester(cls, person_id, semester):
        """
        Return a string representing the rank(s) for this person as of the beginning of a given semester.
        """
        salaries = CareerEvent.objects.filter(person__id=person_id, event_type='SALARY').effective_date(semester.start)
        if not salaries:
            return 'unknown'

        ranks = set(s.get_handler().get_rank_display() for s in salaries)
        return ', '.join(ranks)

    @classmethod
    @cached(6*3600)
    def current_base_salary(cls, person):
        """
        Return a string representing the current base salary for this person.  If the person has more than
        one currently effective one, they get added together.
        """
        salaries = CareerEvent.objects.filter(person=person, event_type='SALARY').effective_now()
        if not salaries:
            return 'unknown'
        # One could theoretically have more than one active base salary (for example, if one is a member of more than
        # one school and gets a salary from both).  In that case, add them up.
        total = Decimal(0)
        for s in salaries:
            if 'base_salary' in s.config:
                total += Decimal(s.config.get('base_salary'))
        # format it nicely with commas, see http://stackoverflow.com/a/10742904/185884
        return str('$' + "{:,}".format(total))


    @classmethod
    @cached(6*3600)
    def current_market_diff(cls, person):
        """
        Return a string representing the current market differential for this person.
        """
        diffs = CareerEvent.objects.filter(person=person, event_type='STIPEND').effective_now()
        if not diffs:
            return 'unknown'
        #  Retention, market differentials, research chair stipends, and other adjustments are stored in the same
        #  stipend type event. We only care about market differentials.
        marketdiffs = [d for d in diffs if 'source' in d.config and d.config.get('source') == 'MARKETDIFF']
        if marketdiffs:
            # Just like base salaries, we could theoretically have more than one active at a given time, we think.
            # Let's add them up in that case
            total = Decimal(0)
            for diff in marketdiffs:
                if 'amount' in diff.config:
                    total += Decimal(diff.config.get('amount'))
            return str('$' + "{:,}".format(total))
        else:
            return 'unknown'


    def get_event_type_display_(self):
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
            himher = 'him'
        elif gender == "F":
            hisher = "her"
            heshe = 'she'
            himher = 'her'
        else:
            hisher = "his/her"
            heshe = 'he/she'
            himher = 'him/her'

        # grab event type specific config data
        handler = self.get_handler()
        config_data = copy.deepcopy(self.config)
        for key in config_data:
            try:
                config_data[key] = str(handler.get_display(key))
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
                'him_her' : himher,
                'Him_Her' : himher.title(),
                'first_name': self.person.first_name,
                'last_name': self.person.last_name,
                'start_date': start,
                'end_date': end,
                'current_rank': CareerEvent.current_ranks(self.person.id),
                'unit': self.unit.name,
                'current_base_salary': CareerEvent.current_base_salary(self.person),
                'current_market_diff': CareerEvent.current_market_diff(self.person),
              }
        ls = dict(list(ls.items()) + list(config_data.items()))
        return ls

    def has_memos(self):
        return Memo.objects.filter(career_event=self, hidden=False).count() > 0

    def has_attachments(self):
        return DocumentAttachment.objects.filter(career_event=self, hidden=False).count() > 0


# https://stackoverflow.com/a/47817197/6871666
CareerEvent.get_event_type_display = CareerEvent.get_event_type_display_


def attachment_upload_to(instance, filename):
    return upload_path('faculty', filename)


def position_attachment_upload_to(instance, filename):
    return upload_path('faculty', 'positions', filename)


class DocumentAttachmentManager(models.Manager):
    def visible(self):
        qs = self.get_queryset()
        return qs.filter(hidden=False)


class DocumentAttachment(models.Model):
    """
    Document attached to a CareerEvent.
    """
    career_event = models.ForeignKey(CareerEvent, null=False, blank=False, related_name="attachments", on_delete=models.PROTECT)
    title = models.CharField(max_length=250, null=True, blank=True)
    slug = AutoSlugField(populate_from='title', null=False, editable=False, unique_with=('career_event',))
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, help_text='Document attachment created by.', on_delete=models.PROTECT)
    contents = models.FileField(storage=UploadedFileStorage, upload_to=attachment_upload_to, max_length=500)
    mediatype = models.CharField(max_length=200, null=True, blank=True, editable=False)
    hidden = models.BooleanField(default=False, editable=False)

    objects = DocumentAttachmentManager()

    def __str__(self):
        return self.contents.name

    class Meta:
        ordering = ("created_at",)
        unique_together = (("career_event", "slug"),)

    def contents_filename(self):
        return os.path.basename(self.contents.name)

    def hide(self):
        self.hidden = True
        self.save()


class MemoTemplate(models.Model):
    """
    A template for memos.
    """
    unit = models.ForeignKey(Unit, null=False, blank=False, on_delete=models.PROTECT)
    label = models.CharField(max_length=150, null=False, verbose_name='Template Name',
                             help_text='The name for this template (that you select it by when using it)')
    event_type = models.CharField(max_length=10, null=False, choices=EVENT_TYPE_CHOICES,
                                  help_text='The type of event that this memo applies to')
    default_from = models.CharField(verbose_name='Default From', help_text='The default sender of the memo',
                                    max_length=255, blank=True)
    subject = models.CharField(verbose_name='Default Subject', help_text='The default subject of the memo. Will be '
                                                                         'ignored for letters', max_length=255)
    is_letter = models.BooleanField(verbose_name="Make it a letter", help_text="Should this be a letter by default",
                                    default=False)
    template_text = models.TextField(help_text="The template for the memo. It may be edited when creating "
                                               "each memo. (i.e. 'Congratulations {{first_name}} on ... ')")

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, help_text='Memo template created by.', related_name='+', on_delete=models.PROTECT)
    hidden = models.BooleanField(default=False)

    def autoslug(self):
        return make_slug(self.unit.label + "-" + self.label)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique=True)

    def __str__(self):
        return "%s in %s" % (self.label, self.unit)

    class Meta:
        unique_together = ('unit', 'label')

    def save(self, *args, **kwargs):
        self.template_text = normalize_newlines(self.template_text.rstrip())
        super(MemoTemplate, self).save(*args, **kwargs)

    def get_event_type_display_(self):
        "Override to display nicely"
        return EVENT_TYPES[self.event_type].NAME


# https://stackoverflow.com/a/47817197/6871666
MemoTemplate.get_event_type_display = MemoTemplate.get_event_type_display_


class Memo(models.Model):
    """
    A memo created by the system, and attached to a CareerEvent.
    """
    career_event = models.ForeignKey(CareerEvent, null=False, blank=False, on_delete=models.PROTECT)
    unit = models.ForeignKey(Unit, null=False, blank=False, on_delete=models.PROTECT, help_text="The unit producing the memo: will determine the "
                                                                      "letterhead used for the memo.")

    sent_date = models.DateField(default=datetime.date.today, help_text="The sending date of the letter")
    to_lines = models.TextField(verbose_name='Attention', help_text='Recipient of the memo', null=True, blank=True)
    cc_lines = models.TextField(verbose_name='CC lines', help_text='Additional recipients of the memo', null=True,
                                blank=True)
    from_person = models.ForeignKey(Person, null=True, related_name='+', on_delete=models.PROTECT)
    from_lines = models.TextField(verbose_name='From', help_text='Name (and title) of the sender, e.g. "John Smith, '
                                                                 'Applied Sciences, Dean"')
    subject = models.TextField(help_text='The subject of the memo (lines will be formatted separately in the memo '
                                         'header). This will be ignored for letters')

    template = models.ForeignKey(MemoTemplate, null=True, on_delete=models.PROTECT)
    is_letter = models.BooleanField(verbose_name="Make it a letter", help_text="Make it a letter with correct "
                                                                               "letterhead instead of a memo.",
                                    default=False)
    memo_text = models.TextField(help_text="I.e. 'Congratulations on ... '")

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, help_text='Letter generation requested by.', related_name='+', on_delete=models.PROTECT)
    hidden = models.BooleanField(default=False)
    config = JSONField(default=dict)  # addition configuration for the memo
    # 'use_sig': use the from_person's signature if it exists?
    #            (Users set False when a real legal signature is required.)
    # 'pdf_generated': set to True if a PDF has ever been created for this memo (used to decide if it's editable)

    use_sig = config_property('use_sig', default=True)

    def autoslug(self):
        if self.template:
            return make_slug(self.career_event.slug + "-" + self.template.label)
        else:
            return make_slug(self.career_event.slug + "-memo")
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique_with=('career_event',))

    def __str__(self):
        return "%s memo for %s" % (self.subject, self.career_event)

    def hide(self):
        self.hidden = True
        self.save()

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

    def uneditable_reason(self):
        """
        Return a string indicating why this memo cannot be edited, or None.
        """
        age = timezone.now() - self.created_at
        if age > datetime.timedelta(minutes=15):
            return 'memo is more than 15 minutes old'
        #elif self.config.get('pdf_generated', False):
        #    return 'PDF has been generated, so we assume it was sent'
        return None

    def write_pdf(self, response):
        from dashboard.letters import OfficialLetter, MemoContents, LetterContents

        # record the fact that it was generated (for editability checking)
        self.config['pdf_generated'] = True
        self.save()

        doc = OfficialLetter(response, unit=self.unit)
        if self.is_letter:
            l = LetterContents(to_addr_lines=self.to_lines.split("\n"),
                               from_name_lines=self.from_lines.split("\n"),
                               date=self.sent_date,
                               cc_lines=self.cc_lines.split("\n"),
                               )
        else:
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
    unit = models.ForeignKey(Unit, null=False, blank=False, on_delete=models.PROTECT)
    event_type = models.CharField(max_length=10, null=False, choices=EVENT_TYPE_CHOICES)
    config = JSONField(default=dict)

    class Meta:
        unique_together = ('unit', 'event_type')


class TempGrantManager(models.Manager):
    def create_from_csv(self, fh, creator, units):
        reader = csv.reader(fh.read().splitlines())
        failed = []
        created = []
        for row in reader:
            try:
                fund = str(row[0].strip(), errors='ignore')
            except IndexError:
                continue
            if re.match('[0-9]{2} ?-? ?[0-9]{6}$', fund):
                try:
                    label = str(row[1].strip(), errors='ignore')
                except IndexError:
                    failed.append(row)
                    continue
                try:
                    # Grab things from the CSV
                    balance = Decimal(str(row[4].strip(), errors='ignore'))
                    cur_month = Decimal(str(row[5].strip(), errors='ignore'))
                    ytd_actual = Decimal(str(row[6].strip(), errors='ignore'))
                    cur_balance = Decimal(str(row[8].strip(), errors='ignore'))
                except (IndexError, InvalidOperation):
                    failed.append(row)
                    continue

                # If Grant with the label already exists, then we update the balance
                try:
                    grant = Grant.objects.get(label=label, unit__in=units)
                except Grant.DoesNotExist:
                    pass
                else:
                    grant.update_balance(cur_balance, cur_month, ytd_actual)

                # Make sure its not a duplicate label for Temp Grants
                if not TempGrant.objects.filter(label=label, creator=creator).exists():
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
    label = models.CharField(max_length=150, help_text="for identification from FAST import")
    initial = models.DecimalField(verbose_name="initial balance", max_digits=12, decimal_places=2)
    project_code = models.CharField(max_length=32, help_text="The fund and project code, like '13-123456'")
    import_key = models.CharField(null=True, blank=True, max_length=255, help_text="e.g. 'nserc-43517b4fd422423382baab1e916e7f63'")
    creator = models.ForeignKey(Person, blank=True, null=True, on_delete=models.PROTECT)
    created = models.DateTimeField(auto_now_add=True)
    config = JSONField(default=dict) # addition configuration for within the temp grant

    objects = TempGrantManager()

    class Meta:
        unique_together = (('label', 'creator'),)

    def get_convert_url(self):
        return reverse("faculty:convert_grant", args=[self.id])

    def get_delete_url(self):
        return reverse("faculty:delete_grant", args=[self.id])

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
        qs = self.get_queryset()
        return qs.filter(status='A')


class Grant(models.Model):
    STATUS_CHOICES = (
        ("A", "Active"),
        ("D", "Deleted"),
    )
    title = models.CharField(max_length=64, help_text='Label for the grant within this system')
    slug = AutoSlugField(populate_from='title', unique_with=("unit",), null=False, editable=False)
    label = models.CharField(max_length=150, help_text="for identification from FAST import", db_index=True)
    owners = models.ManyToManyField(Person, through='GrantOwner', blank=False, help_text='Who owns/controls this grant?')
    project_code = models.CharField(max_length=32, db_index=True, help_text="The fund and project code, like '13-123456'")
    start_date = models.DateField(null=False, blank=False)
    expiry_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default='A')
    initial = models.DecimalField(verbose_name="Initial balance", max_digits=12, decimal_places=2)
    overhead = models.DecimalField(verbose_name="Annual overhead", max_digits=12, decimal_places=2, help_text="Annual overhead returned to Faculty budget")
    import_key = models.CharField(null=True, blank=True, max_length=255, help_text="e.g. 'nserc-43517b4fd422423382baab1e916e7f63'")
    unit = models.ForeignKey(Unit, null=False, blank=False, help_text="Unit who owns the grant", on_delete=models.PROTECT)
    config = JSONField(blank=True, null=True, default=dict)  # addition configuration for within the grant

    objects = GrantManager()

    class Meta:
        unique_together = (('label', 'unit'),)
        ordering = ['title']

    def __str__(self):
        return "%s" % self.title

    def get_absolute_url(self):
        return reverse("faculty:view_grant", kwargs={'unit_slug': self.unit.slug, 'grant_slug': self.slug})

    def update_balance(self, balance, spent_this_month, actual, date=datetime.datetime.today()):
        gb = GrantBalance.objects.create(
            date=date,
            grant=self,
            balance=balance,
            actual=actual,
            month=spent_this_month
        )
        return gb

    def get_owners_display(self, units):
        """
        HTML display of the owners list

        (some logic required since we want to link to faculty profiles if exists && permitted)
        """
        from django.utils.html import conditional_escape as escape
        from django.utils.safestring import mark_safe
        res = []
        for o in self.grantowner_set.all():
            p = o.person
            if Role.objects.filter(unit__in=units, role='FAC', person=p).exists():
                url = reverse('faculty:summary', kwargs={'userid': p.userid_or_emplid()})
                res.append('<a href="%s">%s</a>' %(escape(url), escape(o.person.name())))
            else:
                res.append(escape(o.person.name()))

        return mark_safe(', '.join(res))


class GrantOwner(models.Model):
    grant = models.ForeignKey(Grant, on_delete=models.PROTECT)
    person = models.ForeignKey(Person, on_delete=models.PROTECT)
    config = JSONField(blank=True, null=True, default=dict)  # addition configuration

class GrantBalance(models.Model):
    date = models.DateField(default=datetime.date.today)
    grant = models.ForeignKey(Grant, null=False, blank=False, on_delete=models.PROTECT)
    balance = models.DecimalField(verbose_name="grant balance", max_digits=12, decimal_places=2)
    actual = models.DecimalField(verbose_name="YTD actual", max_digits=12, decimal_places=2)
    month = models.DecimalField(verbose_name="current month", max_digits=12, decimal_places=2)
    config = JSONField(blank=True, null=True, default=dict)  # addition configuration within the memo

    def __str__(self):
        return "%s balance as of %s" % (self.grant, self.date)

    class Meta:
        ordering = ['date']


class FacultyMemberInfo(models.Model):
    person = models.OneToOneField(Person, related_name='+', on_delete=models.PROTECT)
    title = models.CharField(max_length=50)
    birthday = models.DateField(verbose_name="Birthdate", null=True, blank=True)
    office_number = models.CharField('Office', max_length=20, null=True, blank=True)
    phone_number = models.CharField('Local Phone Number', max_length=20, null=True, blank=True)
    emergency_contact = models.TextField('Emergency Contact Information', blank=True)
    config = JSONField(blank=True, null=True, default=dict)  # addition configuration

    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '<FacultyMemberInfo({})>'.format(self.person)

    def get_absolute_url(self):
        return reverse('faculty:faculty_member_info',
                       args=[self.person.userid_or_emplid()])


def timezone_today():
    """
    Return the timezone-aware version of datetime.date.today()

    :return: Today's date corrected for timezones
    """
    return timezone.now().date()


class PositionManager(models.Manager):
    def visible(self):
        qs = self.get_queryset()
        return qs.filter(hidden=False)

    def visible_by_unit(self, units):
        qs = self.get_queryset()
        return qs.filter(hidden=False).filter(unit__in=units)


class Position(models.Model):
    title = models.CharField(max_length=100)
    projected_start_date = models.DateField('Projected Start Date', default=timezone_today)
    unit = models.ForeignKey(Unit, null=False, blank=False, on_delete=models.PROTECT)
    position_number = models.CharField(max_length=8)
    rank = models.CharField(choices=RANK_CHOICES, max_length=50, null=True, blank=True)
    step = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                     help_text='Percentage of this position in the given unit', default=100)
    base_salary = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    add_salary = models.DecimalField(decimal_places=2, max_digits=10,  null=True, blank=True)
    add_pay = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    config = JSONField(null=False, blank=False, editable=False, default=dict)  # For future fields
    hidden = models.BooleanField(default=False, editable=False)
    any_person = models.ForeignKey(AnyPerson, on_delete=models.SET_NULL, null=True, blank=True)
    degree1 = models.CharField(max_length=12, default='')
    year1 = models.CharField(max_length=5, default='')
    institution1 = models.CharField(max_length=25, default='')
    location1 = models.CharField(max_length=23, default='')
    degree2 = models.CharField(max_length=12, default='')
    year2 = models.CharField(max_length=5, default='')
    institution2 = models.CharField(max_length=25, default='')
    location2 = models.CharField(max_length=23, default='')
    degree3 = models.CharField(max_length=12, default='')
    year3 = models.CharField(max_length=5, default='')
    institution3 = models.CharField(max_length=25, default='')
    location3 = models.CharField(max_length=23, default='')
    teaching_semester_credits = models.DecimalField(decimal_places=0, max_digits=3, null=True, blank=True)

    objects = PositionManager()

    def __str__(self):
        return "%s - %s" % (self.position_number, self.title)

    def hide(self):
        self.hidden = True

    class Meta:
        ordering = ('projected_start_date', 'title')

    def get_load_display(self):
        """
        Called if you're going to insert this in another AnnualTeachingCreditField,
        like when we populate the onboarding wizard with this value.
        """
        if 'teaching_load' in self.config and not self.config['teaching_load'] == 'None':
            return str(Fraction(self.config['teaching_load']))

        else:
            return 0

    def get_load_display_corrected(self):
        """
        Called if you're purely going to display the value, as when displaying the contents of the position.
        """
        if 'teaching_load' in self.config and not self.config['teaching_load'] == 'None':
            return str(Fraction(self.config['teaching_load'])*3)

        else:
            return 0


class PositionDocumentAttachmentManager(models.Manager):
    def visible(self):
        qs = self.get_queryset()
        return qs.filter(hidden=False)


class PositionDocumentAttachment(models.Model):
    """
    Document attached to a CareerEvent.
    """
    position = models.ForeignKey(Position, null=False, blank=False, related_name="attachments", on_delete=models.PROTECT)
    title = models.CharField(max_length=250, null=True, blank=True)
    slug = AutoSlugField(populate_from='title', null=False, editable=False, unique_with=('position',))
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, help_text='Document attachment created by.', on_delete=models.PROTECT)
    contents = models.FileField(storage=UploadedFileStorage, upload_to=position_attachment_upload_to, max_length=500)
    mediatype = models.CharField(max_length=200, null=True, blank=True, editable=False)
    hidden = models.BooleanField(default=False, editable=False)

    objects = PositionDocumentAttachmentManager()

    def __str__(self):
        return self.contents.name

    class Meta:
        ordering = ("created_at",)
        unique_together = (("position", "slug"),)

    def contents_filename(self):
        return os.path.basename(self.contents.name)

    def hide(self):
        self.hidden = True
        self.save()
