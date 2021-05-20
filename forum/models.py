import datetime

from django.db import models

from coredata.models import CourseOffering, Member
from courselib.json_fields import JSONField, config_property
from courselib.markup import markup_to_html
from forum import DEFAULT_FORUM_MARKUP
from forum.names_generator import get_random_name


# TODO: subscriptions
# TODO: pinned comments
# TODO: read/unread tracking

IDENTITY_CHOICES = [
    ('FULL', 'Names must be fully visible to instructors and students'),
    ('INST', 'Names must be visible to instructors, but may be anonymous to other students'),
    ('ANON', 'Students may be anonymous to instructors and students'),
]
THREAD_TYPE_CHOICES = [
    ('QUEST', 'Question'),
    ('DISC', 'Discussion'),
]
THREAD_STATUS_CHOICES = [
    ('OPN', 'Open'),
    ('CLO', 'Closed'),
    ('HID', 'Hidden')
]

class Board(models.Model):
    """
    A discussion/Q&A board for the offering, with config
    """
    offering = models.OneToOneField(CourseOffering, on_delete=models.PROTECT)
    config = JSONField(null=False, blank=False, default=dict)

    identity = config_property('identity', default='INST')  # level of anonymity allowed in this course


class AnonymousIdentity(models.Model):
    """
    A student's anonymous identity, used throughout this offering.
    """
    offering = models.OneToOneField(CourseOffering, on_delete=models.PROTECT)
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    name = models.CharField(max_length=100, null=False, blank=False)
    regen_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [
            ('offering', 'member'),
        ]

    @classmethod
    def new(cls, offering: CourseOffering, member: Member, save: bool = True) -> 'AnonymousIdentity':
        name = get_random_name()
        ident = cls(offering=offering, member=member, name=name)
        if save:
            ident.save()
        return ident

    def regenerate(self, save: bool = True):
        self.name = get_random_name()
        self.regen_count += 1
        if save:
            self.save()


class Topic(models.Model):
    """
    A thread category created by the instructor (like "assignments" or "social")
    """
    offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT)
    name = models.CharField(max_length=100, null=False, blank=False)
    order = models.PositiveSmallIntegerField(null=False, blank=False)

    config = JSONField(null=False, blank=False, default=dict)

    class Meta:
        ordering = ['order']
        unique_together = [
            ('offering', 'order'),
        ]


class PostMixin:
    """
    Functionality common to both threads (the starting message) and replies.
    """
    author = models.ForeignKey(Member, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False)
    status = models.CharField(max_length=4, null=False, blank=False, default='OPEN', choices=THREAD_STATUS_CHOICES)
    config = JSONField(null=False, blank=False, default=dict)

    content = config_property('text', default=('', DEFAULT_FORUM_MARKUP, False))  # post content as (text, markup, math:bool)

    def html_content(self):
        text, markuplang, math = self.content
        return markup_to_html(text, markuplang, math=math, restricted=True)


class Thread(models.Model, PostMixin):
    offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT)
    type = models.CharField(max_length=5, null=False, blank=False, default='DISC', choices=THREAD_TYPE_CHOICES)
    title = models.CharField(max_length=255, null=False, blank=False)


class Reply(models.Model, PostMixin):
    thread = models.ForeignKey(Thread, on_delete=models.PROTECT)
    parent = models.ForeignKey('Reply', on_delete=models.PROTECT, null=True, blank=True)  # null == top-level reply
