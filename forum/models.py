import datetime
from typing import Dict, Any

from autoslug import AutoSlugField
from django.db import models, transaction, IntegrityError
from django.core.cache import cache
from django.db.models import Max
from django.http import Http404
from django.urls import reverse

from coredata.models import CourseOffering, Member
from courselib.json_fields import JSONField, config_property
from courselib.markup import markup_to_html
from courselib.slugs import make_slug
from forum import DEFAULT_FORUM_MARKUP
from forum.names_generator import get_random_name


# TODO: subscriptions
# TODO: pinned comments
# TODO: read/unread tracking
# TODO: thread topics
# TODO: instructor-private questions
# TODO: text search


IDENTITY_CHOICES = [  # AnonymousIdentity.identity_choices should reflect any logical changes here
    ('NAME', 'Names must be fully visible to instructors and students'),
    ('INST', 'Names must be visible to instructors, but may be anonymous to other students'),
    ('ANON', 'Students may be anonymous to instructors and students'),
]
THREAD_TYPE_CHOICES = [
    ('QUES', 'Question (i.e. an answer is required)'),
    ('DISC', 'Discussion'),
]
THREAD_STATUS_CHOICES = [
    ('OPEN', 'Open'),
    ('CLOS', 'Closed'),
    ('HIDD', 'Hidden')
]


class Forum(models.Model):
    """
    A discussion/Q&A board for the offering, with config.

    Semantics: forum is only enabled for the course if a Forum object exists and Forum.enabled is True.
    """
    offering = models.OneToOneField(CourseOffering, on_delete=models.PROTECT)
    config = JSONField(null=False, blank=False, default=dict)

    enabled = config_property('enabled', default=True)  # use the discussion forum for this course?
    identity = config_property('identity', default='INST')  # level of anonymity allowed in this course

    @classmethod
    def for_offering_or_404(cls, offering: CourseOffering) -> 'Forum':
        try:
            f = Forum.objects.get(offering=offering)
            if not f.enabled:
                raise Http404('The discussion forum is disabled for this course offering.')
            return f
        except Forum.DoesNotExist:
            raise Http404('The discussion forum is disabled for this course offering.')


class AnonymousIdentity(models.Model):
    """
    A student's anonymous identity, used throughout this offering.
    """
    offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT)
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    name = models.CharField(max_length=100, null=False, blank=False)
    regen_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [
            ('offering', 'member'),
        ]

    @classmethod
    def new(cls, offering: CourseOffering, member: Member, save: bool = True) -> 'AnonymousIdentity':
        assert offering.id == member.offering_id
        name = get_random_name()
        ident = cls(offering=offering, member=member, name=name, regen_count=0)
        if save:
            ident.save()
        return ident

    def regenerate(self, save: bool = True):
        self.name = get_random_name()
        self.regen_count += 1
        if save:
            self.save()

    @classmethod
    def _offering_cache_key(cls, offering_id):
        # we cache .for_offering by this key, for fast retrieval
        return 'AnonymousIdentity-offering-%i' % (offering_id,)

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        # invalidate .for_offering cache
        key = AnonymousIdentity._offering_cache_key(self.offering_id)
        cache.delete(key)
        return result

    @classmethod
    def for_offering(cls, offering_id: int) -> Dict[int, str]:
        """
        Build a mapping of AnonymousIdentity.member.id -> AnonymousIdentity.name, caching it because of frequent usage.
        """
        key = AnonymousIdentity._offering_cache_key(offering_id)
        anon_map = cache.get(key)
        if not anon_map:
            anons = cls.objects.filter(offering_id=offering_id).select_related('member')
            anon_map = {a.member_id: a.name for a in anons}
            cache.set(key, anon_map, timeout=3600)
        return anon_map

    @classmethod
    def for_member(cls, member: Member) -> str:
        """
        Get an AnonymousIdentity.name for this member, creating if necessary.
        """
        anon_map = AnonymousIdentity.for_offering(member.offering_id)
        if member.id in anon_map:
            return anon_map[member.id]
        else:
            # no AnonymousIdentity for this user: create it.
            ident = AnonymousIdentity.new(offering=member.offering, member=member, save=True)
            return ident.name

    @staticmethod
    def real_name(member: Member) -> str:
        """
        The visible real name for this member. (Helper here for consistency.)
        """
        return member.person.name_pref()

    @staticmethod
    def identity_choices(offering_identity, member):
        """
        Allowed identity.choices for an offering with this identity restrictions.
        """
        real_name = AnonymousIdentity.real_name(member)
        anon_name = AnonymousIdentity.for_member(member)
        choices = [
            ('NAME', 'Post with your real name (as “%s”)' % (real_name,))
        ]
        if member.role == 'STUD' and offering_identity == 'ANON':
            choices.append(('ANON', 'Anonymously (as “%s”)' % (anon_name,)))
        if member.role == 'STUD' and offering_identity in ['ANON', 'INST']:
            choices.append(('INST', 'Anonymously to students (as “%s”) but not to instructors (as “%s”)' % (anon_name, real_name)))
        return choices


# class Topic(models.Model):
#     """
#     A thread category created by the instructor (like "assignments" or "social").
#     """
#     offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT)
#     name = models.CharField(max_length=100, null=False, blank=False)
#     order = models.PositiveSmallIntegerField(null=False, blank=False)
#
#     config = JSONField(null=False, blank=False, default=dict)
#
#     class Meta:
#         ordering = ['order']
#         unique_together = [
#             ('offering', 'order'),
#         ]


class Post(models.Model):
    """
    Functionality common to both threads (the starting message) and replies (followup).
    Separated so we can refer to a post (by URL or similar) regardless of its role.
    """
    offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT)  # used to enforce unique number within an offering
    author = models.ForeignKey(Member, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False)
    modified_at = models.DateTimeField(auto_now=True)
    type = models.CharField(max_length=4, null=False, blank=False, default='DISC', choices=THREAD_TYPE_CHOICES)
    status = models.CharField(max_length=4, null=False, blank=False, default='OPEN', choices=THREAD_STATUS_CHOICES)
    number = models.PositiveIntegerField(null=False, blank=False)
    config = JSONField(null=False, blank=False, default=dict)

    content = config_property('content', default='')
    markup = config_property('markup', default=DEFAULT_FORUM_MARKUP)
    math = config_property('math', default=False)
    identity = config_property('identity', default='INST')  # what level of anonymity does this post have?

    class Meta:
        unique_together = [
            ('offering', 'number'),
        ]

    def save(self, *args, **kwargs):
        if self.number:
            return super().save(*args, **kwargs)

        # generate a sequential .number value within this offering
        while True:  # the transaction could fail if two instances are racing: retry in that case.
            with transaction.atomic():
                maxnum = Post.objects.filter(offering=self.offering).aggregate(Max('number'))['number__max']
                if maxnum is None:
                    maxnum = 0
                self.number = maxnum + 1
                try:
                    result = super().save(*args, **kwargs)
                except IntegrityError:
                    pass
                else:
                    return result

    def html_content(self):
        return markup_to_html(self.content, self.markup, math=self.math, restricted=True)

    def visible_author(self, is_instr=False):
        if self.identity == 'NAME' or (self.identity == 'INST' and is_instr):
            return AnonymousIdentity.real_name(self.author)
        else:
            return '“' + AnonymousIdentity.for_member(self.author) + '”'

    def was_edited(self):
        return (self.modified_at - self.created_at) > datetime.timedelta(seconds=5)


class PostStatusManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related('post').exclude(post__status='HIDD')


class Thread(models.Model):
    #offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT)
    title = models.CharField(max_length=255, null=False, blank=False)
    post = models.OneToOneField(Post, on_delete=models.CASCADE)
    pin = models.PositiveSmallIntegerField(default=0)
    #slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique_with=['post__offering'])
    config = JSONField(null=False, blank=False, default=dict)

    objects = PostStatusManager()

    #def autoslug(self):
    #    return make_slug(self.title)

    class Meta:
        ordering = ('-pin', '-post__modified_at')

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.post.save()
            self.post_id = self.post.id
            result = super().save(*args, **kwargs)
        return result

    def get_absolute_url(self):
        return reverse('offering:forum:view_thread', kwargs={'course_slug': self.post.offering.slug, 'post_number': self.post.number})

    def summary_json(self) -> Dict[str, Any]:
        """
        Data for a JSON representation that summarizes the thread (for the menu of threads).
        """
        data = {
            'id': self.id,
            'title': self.title,
            'author': self.post.visible_author(),
            'number': self.post.number,
        }
        return data

    def detail_json(self) -> Dict[str, Any]:
        """
        Data for a JSON representation that is complete thread info. Should be a superset of .summary_json
        """
        data = self.summary_json()
        data['html_content'] = self.post.html_content()
        return data


class Reply(models.Model):
    thread = models.ForeignKey(Thread, on_delete=models.PROTECT)
    parent = models.ForeignKey(Post, on_delete=models.PROTECT, related_name='parent')
    post = models.OneToOneField(Post, on_delete=models.CASCADE)
    config = JSONField(null=False, blank=False, default=dict)

    objects = PostStatusManager()

    class Meta:
        ordering = ('post__modified_at',)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            self.post.save()
            self.post_id = self.post.id
            result = super().save(*args, **kwargs)
        return result
