import datetime
import os

from django.db import models
from django.core.urlresolvers import reverse

from autoslug import AutoSlugField
from bitfield import BitField
from jsonfield import JSONField

from coredata.models import Unit, Person
from courselib.json_fields import config_property
from courselib.slugs import make_slug
from courselib.text import normalize_newlines, many_newlines

from faculty.event_types.awards import FellowshipEventHandler
from faculty.event_types.career import AppointmentEventHandler
from faculty.event_types.career import SalaryBaseEventHandler
from faculty.event_types.career import TenureApplicationEventHandler
from faculty.event_types.career import TenureReceivedEventHandler

# CareerEvent.event_type value -> CareerEventManager class
HANDLERS = [
    AppointmentEventHandler,
    FellowshipEventHandler,
    SalaryBaseEventHandler,
    TenureApplicationEventHandler,
    TenureReceivedEventHandler,
]
EVENT_TYPES = {handler.EVENT_TYPE: handler for handler in HANDLERS}
EVENT_TYPE_CHOICES = EVENT_TYPES.items()

# XXX: There's probably a nicer way to generate this automatically from the mixin classes
EVENT_FLAGS = [
    'affects_teaching',
    'affects_salary',
]


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

    status = models.CharField(max_length=2, choices=STATUS_CHOICES)
    import_key = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def full_title(self):
        return '{} {}'.format(self.start_date.year, self.title)

    def get_absolute_url(self):
        return reverse("faculty_event_view", args=[self.person.userid, self.slug])

    def get_change_url(self):
        return reverse("faculty_change_event", args=[self.person.userid, self.slug])

    def __unicode__(self):
        return self.title

    def save(self, editor, *args, **kwargs):
        # we're doing to so we can add an audit trail later.
        assert editor.__class__.__name__ == 'Person'
        return super(CareerEvent, self).save(*args, **kwargs)

    def get_handler(self):
        return EVENT_TYPE_CHOICES[self.event_type](self)

    class Meta:
        ordering = (
            '-start_date',
            '-end_date',
            'title',
        )


# TODO separate storage system for faculty attachments?
#NoteSystemStorage = FileSystemStorage(location=settings.FACULTY_PATH, base_url=None)
def attachment_upload_to(instance, filename):
    """
    callback to avoid path in the filename(that we have append folder structure to) being striped
    """
    fullpath = os.path.join(
        'faculty',
        instance.person.userid,
        datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S"),
        filename.encode('ascii', 'ignore'))
    return fullpath


class DocumentAttachment(models.Model):
    """
    Document attached to a CareerEvent.
    """
    career_event = models.ForeignKey(CareerEvent, null=False, blank=False)
    title = models.CharField(max_length=250, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Person, help_text='Document attachment created by.')
    contents = models.FileField(upload_to=attachment_upload_to)
    mediatype = models.CharField(max_length=200, null=True, blank=True, editable=False)

    def __unicode__(self):
        return self.contents.filename

    class Meta:
        ordering = ("created_at",)


class MemoTemplate(models.Model):
    """
    A template for memos.
    """
    unit = models.ForeignKey(Unit, null=False, blank=False)
    label = models.CharField(max_length=250, null=False)
    event_type = models.CharField(max_length=10, null=False, choices=EVENT_TYPE_CHOICES)
    template_text = models.TextField(help_text="I.e. 'Congratulations {{first_name}} on ... '")

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


class Memo(models.Model):
    """
    A memo created by the system, and attached to a CareerEvent.
    """
    career_event = models.ForeignKey(CareerEvent, null=False, blank=False)

    sent_date = models.DateField(default=datetime.date.today, help_text="The sending date of the letter, editable")
    to_lines = models.TextField(help_text='Recipient of the memo', null=True, blank=True)
    cc_lines = models.TextField(help_text='additional recipients of the memo', null=True, blank=True)
    from_person = models.ForeignKey(Person, null=True, related_name='+')
    from_lines = models.TextField(help_text='Name (and title) of the signer, e.g. "John Smith, Applied Sciences, Dean"')
    subject = models.TextField(help_text='The career event of the memo')

    template = models.ForeignKey(MemoTemplate, null=True)
    memo_text = models.TextField(help_text="I.e. 'Congratulations Mr. Baker on ... '")
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
        return make_slug(self.career_event.slug + "-" + self.template.memo_type)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=False, unique=True)

    def __unicode__(self):
        return u"%s memo for %s" % (self.template.label, self.career_event)

    def save(self, *args, **kwargs):
        # normalize text so it's easy to work with
        if not self.to_lines:
            self.to_lines = ''
        self.to_lines = normalize_newlines(self.to_lines.rstrip())
        self.from_lines = normalize_newlines(self.from_lines.rstrip())
        self.memo_text = normalize_newlines(self.content.rstrip())
        self.memo_text = many_newlines.sub('\n\n', self.content)
        super(Memo, self).save(*args, **kwargs)


class EventConfig(models.Model):
    """
    A unit's configuration for a particular event type
    """
    unit = models.ForeignKey(Unit, null=False, blank=False)
    event_type = models.CharField(max_length=10, null=False, choices=EVENT_TYPE_CHOICES)
    config = JSONField(default={})
