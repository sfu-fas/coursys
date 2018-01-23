from coredata.models import Member, CourseOffering
from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.conf import settings
from courselib.json_fields import JSONField
from courselib.json_fields import getter_setter
from courselib.branding import product_name
from courselib.markup import ParserFor, ensure_sanitary_markup, markup_to_html
from autoslug import AutoSlugField
from courselib.slugs import make_slug
import datetime

TOPIC_STATUSES = (
                  ('OPN', 'Open'),
                  ('ANS', 'Answered'),
                  ('CLO', 'Closed'),
                  ('HID', 'Hidden'),
                  )

def _time_delta_to_string(time):
    td = datetime.datetime.now() - time
    days, hours, minutes, seconds = td.days, td.seconds / 3600, (td.seconds / 60) % 60, td.seconds
    
    if days is 0:
        if hours is 0:
            if minutes is 0:
                return '%d seconds ago' % seconds
            elif minutes is 1:
                return '1 minute ago'
            else:
                return '%d minutes ago' % minutes
        elif hours is 1:
            return '1 hour ago'
        else:
            return '%d hours ago' % hours
    elif days is 1:
        return '1 day ago'
    elif days < 8:
        return '%d days ago' % days
    else:
        return time.strftime('%b %d, %Y')
    
class DiscussionTopic(models.Model):
    """
    A topic (thread) associated with a CourseOffering
    """
    offering = models.ForeignKey(CourseOffering, null=False, on_delete=models.PROTECT)
    title = models.CharField(max_length=140, help_text="A brief description of the topic")
    content = models.TextField(help_text='The inital message for the topic.')
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now_add=True)
    message_count = models.IntegerField(default=0)
    status = models.CharField(max_length=3, choices=TOPIC_STATUSES, default='OPN', help_text="The topic status: Closed: no replies allowed, Hidden: cannot be seen")
    pinned = models.BooleanField(default=False, help_text="Should this topic be pinned to bring attention?")
    author = models.ForeignKey(Member, on_delete=models.PROTECT)
    def autoslug(self):
        return make_slug(self.title)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique_with=['offering'])
    config = JSONField(null=False, blank=False, default=dict)
        # p.config['markup']:  markup language used: see courselib/markup.py
        # p.config['math']: content uses MathJax? (boolean)
        # p.config['brushes']: used SyntaxHighlighter brushes (list of strings) -- no longer used with highlight.js
    
    defaults = {'markup': 'creole', 'math': False,}
    markup, set_markup = getter_setter('markup')
    math, set_math = getter_setter('math')

    def save(self, *args, **kwargs):
        if self.status not in [status[0] for status in TOPIC_STATUSES]:
            raise ValueError('Invalid topic status')

        self.content = ensure_sanitary_markup(self.content, self.markup(), restricted=True)

        new_topic = self.id is None
        super(DiscussionTopic, self).save(*args, **kwargs)

        # handle subscriptions
        if new_topic:
            subs = DiscussionSubscription.objects.filter(member__offering=self.offering).select_related('member__person')
            for s in subs:
                s.notify(self)
        
    def get_absolute_url(self):
        return reverse('offering:discussion:view_topic', kwargs={'course_slug': self.offering.slug, 'topic_slug': self.slug})

    def new_message_update(self):
        self.last_activity_at = datetime.datetime.now()
        self.message_count = self.message_count + 1
        self.save()
        
    def last_activity_at_delta(self):
        return _time_delta_to_string(self.last_activity_at)
    
    def created_at_delta(self):
        return _time_delta_to_string(self.created_at)
        
    def __str___(self):
        return self.title

    def html_content(self):
        "Convert self.content to HTML"
        return markup_to_html(self.content, self.markup(), offering=self.offering, html_already_safe=True,
                              restricted=True)
    
    def still_editable(self):
        td = datetime.datetime.now() - self.created_at
        seconds = td.days * 86400 + td.seconds
        return seconds <= 120
    
    def editable_time_left(self):
        td = datetime.datetime.now() - self.created_at
        seconds = td.days * 86400 + td.seconds
        if seconds > 120:
            return 'none'
        minutes, seconds = divmod(120 - seconds, 60)
        return "%dm:%ds" % (minutes, seconds)

    def exportable(self):
        """
        Create JSON-serializable representation of topic, for export.
        """
        data = {'title': self.title, 'body': self.content, 'created_at': self.created_at.isoformat(),
                'author': self.author.person.userid, 'status': self.status, 'pinned': self.pinned}
        messages = DiscussionMessage.objects.filter(topic=self).select_related('author__person')
        data['replies'] = [m.exportable() for m in messages]
        return data
        

MESSAGE_STATUSES = (
                  ('VIS', 'Visible'),
                  ('HID', 'Hidden'),
                  )

class DiscussionMessage(models.Model):
    """
    A message (post) associated with a Discussion Topic
    """
    topic = models.ForeignKey(DiscussionTopic, on_delete=models.CASCADE)
    content = models.TextField(blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=3, choices=MESSAGE_STATUSES, default='VIS')
    author = models.ForeignKey(Member, on_delete=models.PROTECT)
    def autoslug(self):
        return make_slug(self.author.person.userid)
    slug = AutoSlugField(populate_from='autoslug', null=False, editable=False, unique_with=['topic'])
    config = JSONField(null=False, blank=False, default=dict)
        # p.config['markup']:  markup language used: see courselib/markup.py
        # p.config['math']: content uses MathJax? (boolean)
        # p.config['brushes']: used SyntaxHighlighter brushes (list of strings) -- no longer used with highlight.js
    
    defaults = {'math': False, 'markup': 'creole'}
    math, set_math = getter_setter('math')
    markup, set_markup = getter_setter('markup')
    #brushes, set_brushes = getter_setter('brushes')

    def save(self, *args, **kwargs):
        if self.status not in [status[0] for status in MESSAGE_STATUSES]:
            raise ValueError('Invalid topic status')
        if not self.pk:
            self.topic.new_message_update()

        self.content = ensure_sanitary_markup(self.content, self.markup(), restricted=True)

        new_message = self.id is None
        super(DiscussionMessage, self).save(*args, **kwargs)

        # handle subscriptions
        if new_message:
            subs = DiscussionSubscription.objects.filter(member__offering=self.topic.offering).select_related('member__person')
            for s in subs:
                s.notify_message(self)
            subs = TopicSubscription.objects.filter(member__offering=self.topic.offering, topic=self.topic).select_related('member__person')
            for s in subs:
                s.notify(self)

    def html_content(self):
        "Convert self.content to HTML"
        return markup_to_html(self.content, self.markup(), offering=self.topic.offering, html_already_safe=True,
                              restricted=True)
    
    def get_absolute_url(self):
        return self.topic.get_absolute_url() + '#reply-' + str(self.id)
    
    def create_at_delta(self):
        return _time_delta_to_string(self.created_at)
    
    def still_editable(self):
        td = datetime.datetime.now() - self.created_at
        seconds = td.days * 86400 + td.seconds
        return seconds <= 120
    
    def editable_time_left(self):
        td = datetime.datetime.now() - self.created_at
        seconds = td.days * 86400 + td.seconds
        if seconds > 120:
            return 'none'
        minutes, seconds = divmod(120 - seconds, 60)
        return "%dm:%ds" % (minutes, seconds)
    
    def was_edited(self):
        td = self.modified_at - self.created_at
        return self.modified_at > self.created_at and td > datetime.timedelta(seconds=3) and self.status != 'HID'

    def exportable(self):
        """
        Create JSON-serializable representation of message, for export.
        """
        data = {'body': self.content, 'created_at': self.created_at.isoformat(),
                'author': self.author.person.userid, 'status': self.status}
        return data



class _DiscussionEmailMixin(object):
    # mixin to avoid copying-and-pasting the email sending logic
    def email_user(self, text_template, html_template, context):
        offering = context['offering']
        headers = {
                'Precedence': 'bulk',
                'Auto-Submitted': 'auto-generated',
                'X-coursys-topic': 'discussion',
                'X-course': offering.slug,
                'Sender': settings.DEFAULT_SENDER_EMAIL,
                }
        to_email = context['to'].email()
        if offering.taemail():
            from_email = "%s <%s>" % (offering.name(), offering.taemail())
        else:
            from_email = settings.DEFAULT_SENDER_EMAIL
        text_content = get_template(text_template).render(context)
        html_content = get_template(html_template).render(context)
        
        msg = EmailMultiAlternatives(context['subject'], text_content, from_email, [to_email], headers=headers)
        msg.attach_alternative(html_content, "text/html")
        msg.send()


TOPIC_SUB_STATUSES = (
                  ('NONE', 'Do nothing'), # == deleted
                  ('MAIL', 'Email me'),
                  )
DISCUSSION_SUB_STATUSES = (
                  ('NONE', 'Do nothing'), # == deleted
                  ('MAIL', 'Email me when a new topic is started'),
                  ('ALLM', 'Email me for new topics and replies'),
                  )

class DiscussionSubscription(models.Model, _DiscussionEmailMixin):
    """
    A member's subscription to their offering's discussion
    """
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    status = models.CharField(max_length=4, choices=DISCUSSION_SUB_STATUSES, default='NONE',
                              verbose_name='Notification',
                              help_text='Action to take when a new topic is posted')

    def notify(self, topic):
        if self.status == 'NONE' or self.member.role == 'DROP':
            pass
        elif self.status in ['MAIL', 'ALLM']:
            url = settings.BASE_ABS_URL + topic.get_absolute_url()
            editurl = settings.BASE_ABS_URL + reverse('offering:discussion:manage_discussion_subscription', 
                    kwargs={'course_slug': self.member.offering.slug})
            subject = 'New discussion in %s' % (topic.offering.name())
            context = {'topic': topic, 'url': url, 'editurl': editurl,
                       'offering': self.member.offering, 'subject': subject,
                       'to': self.member.person, 'author': topic.author, 'CourSys': product_name(hint='course')}
            if self.member.person != topic.author.person:
                self.email_user('discuss/discuss_notify.txt', 'discuss/discuss_notify.html', context)

    def notify_message(self, message):
        "Called when a reply is posted anywhere for this course."
        if self.status in ['NONE', 'MAIL'] or self.member.role == 'DROP':
            pass
        elif self.status == 'ALLM':
            url = settings.BASE_ABS_URL + message.get_absolute_url()
            editurl = settings.BASE_ABS_URL + reverse('offering:discussion:manage_discussion_subscription',
                    kwargs={'course_slug': self.member.offering.slug})
            subject = 'New discussion on "%s"' % (message.topic.title)
            context = {'topic': message.topic, 'message': message, 'url': url, 'editurl': editurl,
                       'offering': message.topic.offering, 'subject': subject,
                       'to': self.member.person, 'author': message.author, 'topic_sub': False,
                       'CourSys': product_name(hint='course')}
            if self.member.person != message.author.person:
                self.email_user('discuss/topic_notify.txt', 'discuss/topic_notify.html', context)

class TopicSubscription(models.Model, _DiscussionEmailMixin):
    """
    A member's subscription to a single discussion topic
    """
    topic = models.ForeignKey(DiscussionTopic, on_delete=models.CASCADE)
    member = models.ForeignKey(Member, on_delete=models.PROTECT)
    status = models.CharField(max_length=4, choices=TOPIC_SUB_STATUSES, default='MAIL',
                              verbose_name='Notification',
                              help_text='Action to take when a new message is posted to this topic')
    class Meta:
        unique_together = (('topic', 'member'),)

    def notify(self, message):
        if self.status == 'NONE' or self.member.role == 'DROP':
            pass
        elif self.status == 'MAIL':
            url = settings.BASE_ABS_URL + message.get_absolute_url()
            editurl = settings.BASE_ABS_URL + reverse('offering:discussion:manage_topic_subscription',
                    kwargs={'course_slug': self.member.offering.slug, 'topic_slug': self.topic.slug})
            subject = 'New discussion on "%s"' % (message.topic.title)
            context = {'topic': self.topic, 'message': message, 'url': url, 'editurl': editurl,
                       'offering': self.topic.offering, 'subject': subject,
                       'to': self.member.person, 'author': message.author, 'topic_sub': True}
            if self.member.person != message.author.person:
                self.email_user('discuss/topic_notify.txt', 'discuss/topic_notify.html', context)

