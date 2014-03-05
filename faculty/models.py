import datetime
import os

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

    def effective_now(self):
        return self.effective_date(datetime.date.today())

    def effective_date(self, date):
        end_okay = Q(end_date__isnull=True) | Q(end_date__gte=date)
        return self.exclude(status='D').filter(start_date__lte=date).filter(end_okay)
    
    def effective_semester(self, semester):
        """
        Returns CareerEvents starting and ending within this semester.
        """
        start, end = Semester.start_end_dates(semester)
        end_okay = Q(end_date__isnull=True) | Q(end_date__lte=end) & Q(end_date__gte=start)
        return self.exclude(status='D').filter(start_date__gte=start).filter(end_okay)

    def overlaps_semester(self, semester):
        """
        Returns CareerEvents occurring during the semester.
        """
        start, end = Semester.start_end_dates(semester)
        end_okay = Q(start_date__lte=end) | Q(end_date__gte=start)
        return self.exclude(status='D').filter(end_okay)

    def within_daterange(self, start, end, inclusive=True):
        if not inclusive:
            filters = {"start_date__gt": start, "end_date__lt": end}
        else:
            filters = {"start_date__gte": start, "end_date__lte": end}
        return self.exclude(status='D').filter(**filters)

    def by_type(self, Handler):
        """
        Returns all CareerEvents matching the given CareerEventHandler class.
        """
        return self.filter(event_type__exact=Handler.EVENT_TYPE)


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

    title = models.CharField(max_length=255, blank=False, null=False)
    slug = AutoSlugField(populate_from='full_title', unique_with=('person', 'unit'),
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
            'title',
        )

    def __unicode__(self):
        return self.title

    def save(self, editor, *args, **kwargs):
        # we're doing to so we can add an audit trail later.
        assert editor.__class__.__name__ == 'Person'
        return super(CareerEvent, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("faculty_event_view", args=[self.person.userid, self.slug])

    def get_attachment_url(self):
        return reverse("faculty_add_attachment", args=[self.person.userid, self.slug])

    def get_status_change_url(self):
        return reverse("faculty_change_event_status", args=[self.person.userid, self.slug])

    def get_change_url(self):
        return reverse("faculty_change_event", args=[self.person.userid, self.slug])

    @property
    def full_title(self):
        return u'{} {} {}'.format(self.start_date.year, self.title, self.unit.label.lower())

    def get_event_type_display(self):
        "Override to display nicely"
        return EVENT_TYPES[self.event_type].NAME

    def get_handler(self):
        if not hasattr(self, 'handler_cache'):
            self.handler_cache = EVENT_TYPES[self.event_type](self)
        return self.handler_cache

    def filter_classes(self):
        """
        return the class="..." value for this event on the summary page (for filtering)
        """
        today = datetime.date.today()
        classes = []
        if self.start_date <= today and (self.end_date == None or self.end_date >= today):
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
        Handler = EVENT_TYPES[self.event_type]
        handler = Handler(self)
        config_data = self.config
        for key in config_data:
            try:
                config_data[key] = unicode(handler.get_display(key))
            except AttributeError:
                pass
        
        ls = { # if changing, also update EVENT_TAGS above!
               # For security reasons, all values must be strings (to avoid presenting dangerous methods in templates)
                'title' : title,
                'his_her' : hisher,
                'His_Her' : hisher.title(),
                'he_she' : heshe,
                'He_She' : heshe.title(),
                'first_name': self.person.first_name,
                'last_name': self.person.last_name,
                'start_date': self.start_date,
                'end_date': self.end_date,
                'event_title': self.title,
              }
        ls = dict(ls.items() + config_data.items())
        return ls


# TODO separate storage system for faculty attachments?
#NoteSystemStorage = FileSystemStorage(location=settings.FACULTY_PATH, base_url=None)
def attachment_upload_to(instance, filename):
    """
    callback to avoid path in the filename(that we have append folder structure to) being striped
    """
    fullpath = os.path.join(
        'faculty',
        instance.created_by.userid,
        datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
        filename.encode('ascii', 'ignore'))
    return fullpath


class DocumentAttachment(models.Model):
    """
    Document attached to a CareerEvent.
    """
    career_event = models.ForeignKey(CareerEvent, null=False, blank=False, related_name="attachments")
    title = models.CharField(max_length=250, null=False)
    slug = AutoSlugField(populate_from='title', null=False, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, help_text='Document attachment created by.')
    contents = models.FileField(upload_to=attachment_upload_to)
    mediatype = models.CharField(max_length=200, null=True, blank=True, editable=False)

    def __unicode__(self):
        return self.contents.filename

    class Meta:
        ordering = ("created_at",)
        unique_together = (("career_event", "slug"),)


class MemoTemplate(models.Model):
    """
    A template for memos.
    """
    unit = models.ForeignKey(Unit, null=False, blank=False)
    label = models.CharField(max_length=250, null=False, verbose_name='Template Name',
                             help_text='The name for this template (that you select it by when using it)')
    event_type = models.CharField(max_length=10, null=False, choices=EVENT_TYPE_CHOICES,
                                  help_text='The type of event that this memo applies to')
    subject = models.CharField(help_text='The default subject of the memo', max_length=255)
    template_text = models.TextField(help_text="The template for the memo. It may be edited when creating "
            "each memo. (i.e. 'Congratulations {{first_name}} on ... ')")

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, help_text='Memo template created by.', related_name='+')
    hidden = models.BooleanField(default=False)

    def autoslug(self):
        return make_slug(self.unit.label + "-" + self.label)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False)

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
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)

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











