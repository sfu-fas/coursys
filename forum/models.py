import datetime
import hashlib
import random
from collections import Counter
from typing import Dict, Any, List

from courselib.branding import product_name
from courselib.search import haystack_index
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import models, transaction, IntegrityError
from django.db.models import Max
from django.http import Http404
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe

from coredata.models import CourseOffering, Member
from courselib.json_fields import JSONField, config_property
from courselib.markup import markup_to_html
from forum import DEFAULT_FORUM_MARKUP
from forum.names_generator import get_random_name


# TODO: something if there are more than THREAD_LIST_MAX threads in the menu
# TODO: better highlighting of unread replies
# TODO: better highlighting of instructor content
# TODO: better highlighting of "approved" answers or instructor approvals

# future TODOs...
# TODO: thread categories
# TODO: should a Reply have type for followup-question?
# TODO: nice to have instructor interaction: make public and anonymous
# TODO: some kind of display of post history
# TODO: instructors can't be anonymous, so don't configure in avatar_form

IDENTITY_CHOICES = [  # Identity.identity_choices should reflect any logical changes here
    ('NAME', 'Names must be fully visible to instructors and students'),
    ('INST', 'Names must be visible to instructors, but may be anonymous to other students'),
    ('ANON', 'Students may be anonymous to instructors and students'),
]
POST_TYPE_CHOICES = [
    ('QUES', 'Question'),
    ('DISC', 'Discussion'),
]
POST_STATUS_CHOICES = [
    ('OPEN', 'Open'),
    ('ANSW', 'Answered'),
    ('NOAN', 'No Answer Needed'),
    ('LOCK', 'Closed to further replies'),  # not implemented
    ('HIDD', 'Hidden'),
]
TITLE_SHORT_LEN = 60  # characters to truncate a title for summary display


def how_long_ago(time: datetime.datetime) -> SafeString:
    """
    Human-readable HTML description of how long ago this was.
    """
    td = datetime.datetime.now() - time
    days, hours, minutes = td.days, td.seconds // 3600, (td.seconds // 60) % 60

    if days < 1:
        if hours < 1:
            if minutes < 1:
                descr = 'just now'
            elif minutes == 1:
                descr = '1 minute ago'
            else:
                descr = '%d minutes ago' % (minutes,)
        elif hours == 1:
            descr = '1 hour ago'
        else:
            descr = '%d hours ago' % (hours,)
    elif days == 1:
        descr = '1 day ago'
    elif days < 8:
        descr = '%d days ago' % (days,)
    else:
        descr = time.strftime('%b %d')

    isodate = time.isoformat()
    return mark_safe('<time datetime="%s" title="%s">%s</time>' % (isodate, isodate, escape(descr)))


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


REGEN_MAX = 5  # maximum number of times a user may regenerate their pseudonym
REGEN_POST_MAX = 5  # maximum number of posts before regeneration locked
AVATAR_TYPE_CHOICES = [
    ('none', 'No avatar image'),
    ('gravatar', 'Gravatar'),
    ('wavatar', 'Gravatar “wavatar” generated avatar'),
    ('retro', 'Gravatar “retro” generated avatar'),
    ('robohash', 'Gravatar “robohash” generated avatar'),
]
DIGEST_FREQUENCY_CHOICES = [
    (1, 'every hour'),
    (3, 'every 3 hours'),
    (6, 'every 6 hours'),
    (24, 'every 24 hours'),
]
INSTR_DEFAULT_FREQUENCY = 24


class Identity(models.Model):
    """
    A forum identity, used throughout this offering. Created for all users, whether .pseudonym is used or not.

    .offering is technically redundant, but allows the correct unique_together keys
    """
    offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT)
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    pseudonym = models.CharField(max_length=100, null=False, blank=False)
    digest_frequency = models.PositiveIntegerField(default=None, null=True, blank=True, choices=DIGEST_FREQUENCY_CHOICES)
    last_digest = models.DateTimeField(default='2000-01-01', null=False, blank=False)  # when was user last sent an email with recent activity?
    config = JSONField(null=False, blank=False, default=dict)

    avatar_type = config_property('avatar_type', default='none')
    anon_avatar_type = config_property('anon_avatar_type', default='none')
    regen_count = config_property('regen_count', default=0)

    class Meta:
        unique_together = [
            ('offering', 'member'),
            ('offering', 'pseudonym'),
        ]

    @classmethod
    def new(cls, offering: CourseOffering, member: Member, save: bool = True) -> 'Identity':
        assert offering.id == member.offering_id
        while True:
            name = get_random_name()
            if not cls.objects.filter(offering=offering, pseudonym=name).exists():
                # Ensure unique name within offering. Technically races with other instances, but I'll take my chances.
                break
        ident = cls(offering=offering, member=member, pseudonym=name, regen_count=0)
        if member.role in APPROVAL_ROLES:
            ident.digest_frequency = INSTR_DEFAULT_FREQUENCY
        if save:
            ident.save()
        return ident

    def regenerate(self, save: bool = True):
        self.pseudonym = get_random_name()
        self.regen_count = self.regen_count + 1
        if save:
            self.save()

    @classmethod
    def for_member(cls, member: Member) -> 'Identity':
        """
        Get an Identity for this member, creating if necessary.
        """
        try:
            return Identity.objects.get(offering_id=member.offering_id, member=member)
        except Identity.DoesNotExist:
            # no Identity for this user: create it.
            ident = Identity.new(offering=member.offering, member=member, save=True)
            return ident

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
        real_name = Identity.real_name(member)
        anon_name = Identity.for_member(member).pseudonym
        choices = [
            ('NAME', 'Post with your real name (as “%s”)' % (real_name,))
        ]
        if member.role == 'STUD' and offering_identity == 'ANON':
            choices.append(('ANON', 'Anonymously (as “%s”)' % (anon_name,)))
        if member.role == 'STUD' and offering_identity in ['ANON', 'INST']:
            choices.append(('INST', 'Anonymously to students (as “%s”) but not to instructors/TAs (as “%s”)' % (anon_name, real_name)))
        return choices

    def avatar_image_url(self, anon: bool, avatar_type=None) -> str:
        if not avatar_type:
            avatar_type = self.avatar_type

        email = self.member.person.email().strip().lower()
        if anon:
            # use a fake not-really-email but consistent string for anonymous gravatars
            email += email
        md5 = hashlib.md5(email.encode('ascii', errors='ignore')).hexdigest()

        if avatar_type == 'gravatar':
            # https://en.gravatar.com/site/implement/images/
            return 'https://www.gravatar.com/avatar/' + md5 + '?r=g&s=160'
        elif avatar_type in ['wavatar', 'retro', 'robohash']:
            return 'https://www.gravatar.com/avatar/' + md5 + '?r=g&s=160&d=' + avatar_type + '&f=y'
        else:
            return ''


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
    Separated so we can refer to a post (by URL or similar) regardless of its role, and unify other functionality.
    """
    offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT)  # used to enforce unique .number within an offering
    author = models.ForeignKey(Member, on_delete=models.PROTECT)
    # Identity used: technically redundant, but allows .select_related for display
    author_identity = models.ForeignKey(Identity, on_delete=models.PROTECT, null=False, blank=False)
    created_at = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False)
    modified_at = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False)
    type = models.CharField(max_length=4, null=False, blank=False, default='DISC', choices=POST_TYPE_CHOICES)
    status = models.CharField(max_length=4, null=False, blank=False, default='OPEN', choices=POST_STATUS_CHOICES)
    number = models.PositiveIntegerField(null=False, blank=False)
    config = JSONField(null=False, blank=False, default=dict)

    content = config_property('content', default='')
    markup = config_property('markup', default=DEFAULT_FORUM_MARKUP)
    math = config_property('math', default=False)
    identity = config_property('identity', default='INST')  # what level of anonymity does this post have?
    marked_answered = config_property('marked_answered', default=False)  # has the asker explicitly marked this as "answered"?
    answered_reason = config_property('answered_reason', default=None)  # why is this considered "answered"?
    instr_answer = config_property('instr_answer', default=False)  # an instructor-written answer exists
    approved_answer = config_property('approved_answer', default=False)  # an instructor-approved answer exists
    asker_approved_answer = config_property('asker_approved_answer', default=False)  # an asker-approved answer exists

    class Meta:
        unique_together = [
            ('offering', 'number'),
        ]

    def save(self, real_change=False, *args, **kwargs):
        if real_change:
            # something worth noting changed
            self.modified_at = datetime.datetime.now()

        # enforce rules for the .author_identity field
        if not self.author_identity_id:
            # not filled: do it ourselves
            self.author_identity = Identity.for_member(self.author)
        else:
            assert self.author_id == self.author_identity.member_id
            assert self.offering_id == self.author_identity.offering_id

        if self.number:
            # we already have our unique post number: the rest is easy.
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

    def get_absolute_url(self):
        # if view_thread encounters a Reply and not a Thread, it will redirect
        return reverse('offering:forum:view_thread', kwargs={'course_slug': self.offering.slug, 'post_number': self.number})

    def html_content(self):
        return markup_to_html(self.content, self.markup, math=self.math, restricted=True, forum_links=True)

    def sees_real_name(self, viewer: Member) -> bool:
        return self.identity == 'NAME' or (self.identity == 'INST' and viewer.role != 'STUD')

    def visible_author(self, viewer: Member) -> str:
        if self.identity == 'NAME':
            return self.author_identity.real_name(self.author)
        elif self.identity == 'INST' and viewer.role != 'STUD':
            return '%s (anonymous to students)' % (self.author_identity.real_name(self.author),)
        else:
            return '“%s”' % (self.author_identity.pseudonym,)

    def visible_author_short(self) -> str:
        if self.identity == 'NAME':
            return self.author_identity.real_name(self.author)
        else:
            return '“%s”' % (self.author_identity.pseudonym,)

    def author_userid(self, viewer: Member) -> str:
        if self.identity == 'NAME':
            return self.author.person.userid
        elif self.identity == 'INST' and viewer.role != 'STUD':
            return self.author.person.userid
        else:
            return None

    def was_edited(self):
        return (self.modified_at - self.created_at) > datetime.timedelta(seconds=5)

    def editable_by(self, member: Member) -> bool:
        return self.author == member or member.role in ['INST', 'TA']

    def created_at_html(self) -> SafeString:
        return how_long_ago(self.created_at)

    def modified_at_html(self) -> SafeString:
        return how_long_ago(self.modified_at)

    def update_status(self, commit=False) -> None:
        """
        Update self.status (and friends) with the rules of the system:
        - non-questions don't need an answer
        - questions are answered if:
            - an instructor/TA has given an answer,
            - an instructor/TA has reacted positively an answer,
            - the question-asker has reacted positively an answer,
            - the question-asker has marked it answered.
        - other questions are unanswered (open).

        Post.update_status should be called from any code that affects these factors.
        """
        if self.status in ['HIDD', 'LOCK']:
            return

        replies = Reply.objects.filter(parent=self).select_related('post', 'post__author')

        if self.type != 'QUES':
            self.status = 'NOAN'

        else:
            self.status = 'OPEN'

            post_ids = [r.post_id for r in replies]
            approvals = Reaction.objects.filter(
                post_id__in=post_ids,
                member__role__in=APPROVAL_ROLES,
                reaction__in=APPROVAL_REACTIONS
            )
            self.approved_answer = approvals.exists()
            if self.approved_answer:
                # there's an instructor-approved answer
                self.status = 'ANSW'
                self.answered_reason = 'REACT'

            approvals = Reaction.objects.filter(
                post_id__in=post_ids,
                member=self.author,
                reaction__in=APPROVAL_REACTIONS
            )
            self.asker_approved_answer = approvals.exists()
            if self.asker_approved_answer:
                # there's an asker-approved answer
                self.status = 'ANSW'
                self.answered_reason = 'AREACT'

            self.instr_answer = replies.filter(post__author__role__in=APPROVAL_ROLES).exists()
            if self.instr_answer:
                # there's an answer from an instructor
                self.status = 'ANSW'
                self.answered_reason = 'INST'

            if self.marked_answered:
                # asker has marked it answered
                self.status = 'ANSW'
                self.answered_reason = 'ASKER'

        if commit:
            self.save()

    def as_json(self, viewer: Member, reaction_data: Dict[int, List['Reaction']]) -> Dict[str, Any]:
        data = {
            'number': self.number,
            'author': self.visible_author(viewer),
            'author_username': self.author_userid(viewer),
            'content_html': self.html_content(),
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat(),
            'type': self.type,
            'identity': self.identity,
        }
        reactions = reaction_data.get(self.id, [])
        data['instructor_reactions'] = Counter(r.reaction for r in reactions if r.member.role in APPROVAL_ROLES)
        data['student_reactions'] = Counter(r.reaction for r in reactions if r.member.role not in APPROVAL_ROLES)
        return data


THREAD_PRIVACY_CHOICES = [
    ('ALL', 'Viewable by students'),
    ('INST', 'Private question to instructors/TAs')
]


class Thread(models.Model):
    class ThreadQuerySet(models.QuerySet):
        def filter_for(self, member: Member):
            # logic here is replicated in views.search for the SearchQuerySet
            qs = self.filter(post__offering_id=member.offering_id)
            if member.role == 'STUD':
                qs = qs.filter(models.Q(privacy='ALL') | models.Q(post__author=member))
            return qs

    class ThreadManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().select_related('post').exclude(post__status='HIDD')

    title = models.CharField(max_length=255, null=False, blank=False)
    post = models.OneToOneField(Post, on_delete=models.CASCADE)
    pin = models.PositiveSmallIntegerField(default=0)
    privacy = models.CharField(max_length=4, null=False, blank=False, default='ALL', choices=THREAD_PRIVACY_CHOICES)
    # most recent post under this thread, so we can easily order by activity
    last_activity = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False)
    config = JSONField(null=False, blank=False, default=dict)

    was_broadcast = config_property('was_broadcast', False)  # was this an broadcast_announcement thread that was pushed?

    objects = ThreadManager.from_queryset(ThreadQuerySet)()

    class Meta:
        ordering = ('-pin', '-last_activity')

    @staticmethod
    def sort_key(self):  # so we can take a list of Thread and .sort(key=Thread.sort_key)
        return (-self.pin, -self.last_activity.timestamp())

    def save(self, real_change=False, create_history=False, *args, **kwargs):
        # real_change: user-noticeable changes that should bump last_updated and clear "read" statuses
        with transaction.atomic():
            self.post.save(real_change=real_change)
            self.post_id = self.post.id
            if real_change:
                self.last_activity = datetime.datetime.now()
            result = super().save(*args, **kwargs)

            if create_history:
                history = PostHistory.from_thread(self)
                history.save()

            if real_change:
                # something worth noting changed: mark unread for everybody
                ReadThread.objects.filter(thread_id=self.id).delete()

        self.index_now()
        return result

    def get_absolute_url(self):
        return self.post.get_absolute_url()

    def title_short(self) -> str:
        if len(self.title) < TITLE_SHORT_LEN:
            return self.title
        else:
            return self.title[:TITLE_SHORT_LEN] + '\u2026'

    def last_activity_html(self) -> SafeString:
        return how_long_ago(self.last_activity)

    def as_json(self, viewer: Member, reaction_data: Dict[int, List['Reaction']]) -> Dict[str, Any]:
        """
        Data for a JSON representation that summarizes the thread (for JSON dump).
        """
        data = self.post.as_json(viewer=viewer, reaction_data=reaction_data)
        data.update({
            'title': self.title,
            'replies': [],
        })
        return data

    def broadcast_announcement(self):
        """
        Email contents of this post to everyone in the course.
        """
        url = settings.BASE_ABS_URL + self.post.get_absolute_url()
        title = self.title_short()

        text_content = f'''The instructor has broadcast an announcement from the discussion forum on {product_name(hint='course')} which you can view here: {url}'''
        html_content = f'''<base href="{escape(url)}" />
            <p style="font-size: smaller; font-style: italic;">[The instructor has broadcast this {product_name(hint='course')}
            discussion forum post as an announcement to the class.
            You can also view it on {product_name(hint='course')}:
            <a href="{escape(url)}">#{self.post.number} {escape(title)}</a>.]</p>'''
        html_content += self.post.html_content()
        html_content += f'''
            <p style="font-size: smaller; border-top: 1px solid black;">You received this email from {product_name(hint='course')}.
            The course instructor/TA requested that it be broadcast as an announcement to all students.
            You cannot unsubscribe from these messages, but we do ask instructors to use them sparingly.</p>
            '''

        subject = f'{self.post.offering.name()}: {title}'
        from_email = self.post.author.person.full_email()

        headers = {
            'Precedence': 'bulk',
            'Auto-Submitted': 'auto-generated',
            'X-coursys-topic': 'forum',
            'X-course': self.post.offering.slug,
        }

        members = Member.objects.exclude(role='DROP').filter(offering=self.post.offering).select_related('person')
        members = list(members)
        random.shuffle(members)

        for m in members:
            to_email = m.person.email()
            if not to_email:
                continue
            msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email], headers=headers)
            msg.attach_alternative(html_content, "text/html")
            msg.send()

    def index_now(self):
        """
        Create/update haystack index of this thread.
        """
        haystack_index(Thread, [self])


class Reply(models.Model):
    class ReplyQuerySet(models.QuerySet):
        def filter_for(self, member: Member):
            qs = self.filter(post__offering_id=member.offering_id)
            if member.role == 'STUD':
                qs = qs.filter(models.Q(thread__privacy='ALL') | models.Q(thread__post__author=member))
            return qs

    class ReplyManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().select_related('post').exclude(post__status='HIDD')

    thread = models.ForeignKey(Thread, on_delete=models.PROTECT)
    parent = models.ForeignKey(Post, on_delete=models.PROTECT, related_name='parent')
    post = models.OneToOneField(Post, on_delete=models.CASCADE)
    config = JSONField(null=False, blank=False, default=dict)

    objects = ReplyManager.from_queryset(ReplyQuerySet)()

    class Meta:
        ordering = ('post__created_at',)

    def save(self, real_change=False, create_history=False, *args, **kwargs):
        # real_change: user-noticeable changes that should bump last_updated and clear "read" statuses
        with transaction.atomic():
            self.post.save(real_change=real_change)
            self.post_id = self.post.id
            # the .update should be an one-field update, not risking racing some other process
            Thread.objects.filter(id=self.thread_id).update(last_activity=datetime.datetime.now())
            result = super().save(*args, **kwargs)

            if create_history:
                history = PostHistory.from_reply(self)
                history.save()

            if real_change:
                # something worth noting changed: mark unread for everybody
                ReadThread.objects.filter(thread_id=self.thread_id).delete()
                ReadReply.objects.filter(reply_id=self.id).delete()

        self.thread.index_now()
        return result

    def get_absolute_url(self, fragment=False):
        return self.thread.get_absolute_url() + ('?fragment=yes' if fragment else '') + '#post-' + str(self.post.number)

    def as_json(self, viewer: Member, reaction_data: Dict[int, List['Reaction']]) -> Dict[str, Any]:
        """
        Data for a JSON representation that summarizes the thread (for JSON dump).
        """
        return self.post.as_json(viewer=viewer, reaction_data=reaction_data)


class PostHistory(models.Model):
    """
    A historic record of the state of a Post (and associated Thread or Reply).
    """
    post = models.ForeignKey(Post, on_delete=models.PROTECT, null=False, blank=False)
    thread = models.ForeignKey(Thread, on_delete=models.PROTECT, null=True, blank=True)
    reply = models.ForeignKey(Reply, on_delete=models.PROTECT, null=True, blank=True)
    created_at = models.DateTimeField(default=datetime.datetime.now, null=False, blank=False)
    config = JSONField(null=False, blank=False, default=dict)

    def save(self, *args, **kwargs):
        assert self.thread or self.reply
        assert (not self.thread) or self.thread.post_id == self.post_id
        assert (not self.reply) or self.reply.post_id == self.post_id

        return super().save(*args, **kwargs)

    @classmethod
    def from_thread(cls, thread: Thread) -> 'PostHistory':
        h = PostHistory(thread=thread, post=thread.post, reply=None)
        h.config = thread.post.config.copy()
        h.config.update(thread.config)
        h.config['title'] = thread.title
        h.config['privacy'] = thread.privacy
        h.config['pin'] = thread.pin
        h.config['type'] = thread.post.type
        h.config['status'] = thread.post.status
        return h

    @classmethod
    def from_reply(cls, reply: Reply) -> 'PostHistory':
        h = PostHistory(reply=reply, post=reply.post, thread=None)
        h.config = reply.post.config.copy()
        h.config.update(reply.config)
        return h


class ReadThread(models.Model):
    """
    This user has read this Thread *and* and Replies, as they exist (i.e. should be deleted on a reply edit)
    """
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    thread = models.ForeignKey(Thread, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True, null=False, blank=False)

    class Meta:
        unique_together = [
            ('member', 'thread'),
        ]

    @staticmethod
    def mark_all_read(member: Member):
        threads = Thread.objects.filter(post__offering_id=member.offering_id)
        ReadThread.objects.bulk_create(
            [ReadThread(member=member, thread_id=t.id) for t in threads],
            ignore_conflicts=True
        )


class ReadReply(models.Model):
    """
    This user has read this Reply, as it exists (i.e. should be deleted on edit)
    """
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    reply = models.ForeignKey(Reply, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True, null=False, blank=False)

    class Meta:
        unique_together = [
            ('member', 'reply'),
        ]


REACTION_CHOICES = [
    ('UP', 'Thumbs Up'),
    ('LOVE', 'Love'),
    ('CLAP', 'Clap'),
    ('LAUG', 'Laugh'),
    ('CONF', 'Confused'),
    #('DOWN', 'Thumbs Down'),
    ('NONE', 'no reaction'),
]
REACTION_ICONS = {  # emoji for the reaction
    'NONE': '\U0000274C',
    'UP': '\U0001F44D',
    #'DOWN': '\U0001F44E',
    'LAUG': '\U0001F923',
    'LOVE': '\U00002764\U0000FE0F',
    'CLAP': '\U0001F44F',
    'CONF': '\U0001F615',
}
REACTION_SCORES = {  # score for the reaction, for "sort by best" and any values >=1 mean "answered".
    'NONE': 0,
    'UP': 1,
    #'DOWN': -1,
    'LAUG': 0.5,
    'LOVE': 1,
    'CLAP': 1,
    'CONF': -0.5,
}
REACTION_DESCRIPTIONS = dict(REACTION_CHOICES)
SCORE_STAFF_FACTOR = 2  # weight factor for score of an instructor/TA reaction
APPROVAL_REACTIONS = [reaction for reaction,score in REACTION_SCORES.items() if score >= 1]
APPROVAL_ROLES = ['INST', 'TA']  # Member.role value we consider to be automatic-answerers or approvers


class Reaction(models.Model):
    """
    User has reacted to this post, and how.
    """
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    reaction = models.CharField(max_length=4, null=False, blank=False, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now=True, null=False, blank=False)

    class Meta:
        unique_together = [
            ('member', 'post'),
        ]

    def __str__(self):
        return '%s says %s' % (self.member.person.name_pref(), REACTION_ICONS[self.reaction])
