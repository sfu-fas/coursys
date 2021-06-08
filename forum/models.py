import datetime
import hashlib

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


# TODO: subscriptions/configurable digest emails
# TODO: thread categories
# TODO: re-roll of anonymousidentity if reasonably early
# TODO: should a Reply have type for followup-question?
# TODO: asker should be able to explicitly mark "answered"
# TODO: actual deleting of posts (status='HIDD') by instructors
# TODO: "#123" should be a link to post 123
# TODO: need instructor reply form: no identity field, and "don't consider this an answer" check
# TODO: something if there are more than THREAD_LIST_MAX threads in the menu
# TODO: instr edit shouldn't see/change anon identity setting
# TODO: refactor HaveRead for easier read: ReadThread and ReadReply?


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


AVATAR_TYPE_CHOICES = [
    ('none', 'No avatar image'),
    ('gravatar', 'Gravatar'),
    ('wavatar', 'Gravatar “wavatar” generated avatar'),
    ('retro', 'Gravatar “retro” generated avatar'),
    ('robohash', 'Gravatar “robohash” generated avatar'),
]


class Identity(models.Model):
    """
    A forum identity, used throughout this offering. Created for all users, whether .name is used or not.
    """
    offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT)
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    pseudonym = models.CharField(max_length=100, null=False, blank=False)
    regen_count = models.PositiveIntegerField(default=0)
    config = JSONField(null=False, blank=False, default=dict)

    avatar_type = config_property('avatar_type', default='none')
    anon_avatar_type = config_property('anon_avatar_type', default='none')

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
        if save:
            ident.save()
        return ident

    def regenerate(self, save: bool = True):
        self.pseudonym = get_random_name()
        self.regen_count += 1
        if save:
            self.save()

    @classmethod
    def for_member(cls, member: Member) -> 'Identity':
        """
        Get an Identity for this member, creating if necessary.
        """
        try:
            return Identity.objects.get(member=member)
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
    # Anonymous identity used: technically redundant, but allows .select_related for display
    anon_identity = models.ForeignKey(Identity, on_delete=models.PROTECT, null=True, blank=True)
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
            if self.id:
                HaveRead.objects.filter(post_id=self.id).delete()

        # enforce rules for the .anon_identity field
        if not self.anon_identity:  # not really needed if self.identity=='NAME' but it lets us use the helpers
            # not filled: do it ourselves
            self.anon_identity = Identity.for_member(self.author)
        else:
            assert self.author_id == self.anon_identity.member_id
            assert self.offering_id == self.anon_identity.offering_id

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
            return self.anon_identity.real_name(self.author)
        elif self.identity == 'INST' and viewer.role != 'STUD':
            return '%s (“%s” to students)' % (self.anon_identity.real_name(self.author), self.anon_identity.pseudonym,)
        else:
            return '“%s”' % (self.anon_identity.pseudonym,)

    def visible_author_short(self) -> str:
        if self.identity == 'NAME':
            return self.anon_identity.real_name(self.author)
        else:
            return '“%s”' % (self.anon_identity.pseudonym,)

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
        replies = Reply.objects.filter(parent=self).select_related('post', 'post__author')
        if self.status == 'HIDD':
            return

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


THREAD_PRIVACY_CHOICES = [
    ('ALL', 'Viewable by students'),
    ('INST', 'Private question to instructors/TAs')
]


class Thread(models.Model):
    class ThreadQuerySet(models.QuerySet):
        def filter_for(self, member: Member):
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

    objects = ThreadManager.from_queryset(ThreadQuerySet)()

    class Meta:
        ordering = ('-pin', '-last_activity')

    @staticmethod
    def sort_key(self):  # so we can take a list of Thread and .sort(key=Thread.sort_key)
        return (-self.pin, -self.last_activity.timestamp())

    def save(self, real_change=False, create_history=False, *args, **kwargs):
        with transaction.atomic():
            self.post.save(real_change=real_change)
            self.post_id = self.post.id
            self.last_activity = datetime.datetime.now()
            result = super().save(*args, **kwargs)

            if create_history:
                history = PostHistory.from_thread(self)
                history.save()

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

    # def summary_json(self, viewer: Member) -> Dict[str, Any]:
    #     """
    #     Data for a JSON representation that summarizes the thread (for the menu of threads).
    #     """
    #     data = {
    #         'id': self.id,
    #         'title': self.title,
    #         'author': self.post.visible_author(viewer),
    #         'number': self.post.number,
    #     }
    #     return data
    #
    # def detail_json(self) -> Dict[str, Any]:
    #     """
    #     Data for a JSON representation that is complete thread info. Should be a superset of .summary_json
    #     """
    #     data = self.summary_json()
    #     data['html_content'] = self.post.html_content()
    #     return data


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
        with transaction.atomic():
            self.post.save(real_change=real_change)
            self.post_id = self.post.id
            # the .update should be an one-field update, not risking racing some other process
            Thread.objects.filter(id=self.thread_id).update(last_activity=datetime.datetime.now())
            result = super().save(*args, **kwargs)

            if create_history:
                history = PostHistory.from_reply(self)
                history.save()

        return result

    def get_absolute_url(self):
        return self.thread.get_absolute_url() + '#post-' + str(self.post.number)


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


class HaveRead(models.Model):
    """
    This user has read this post.
    """
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    updated_at = models.DateTimeField(auto_now=True, null=False, blank=False)

    class Meta:
        unique_together = [
            ('member', 'post'),
        ]

    @staticmethod
    def mark_all_read(member: Member):
        posts = Post.objects.filter(offering_id=member.offering_id)
        HaveRead.objects.bulk_create(
            [HaveRead(member=member, post_id=p.id) for p in posts],
            ignore_conflicts=True
        )


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