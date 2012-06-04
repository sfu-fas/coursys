from coredata.models import CourseOffering, Member
from django.db import models
from jsonfield.fields import JSONField
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
    elif days < 60:
        return '%d days ago' % days
    else:
        return time.strftime('%b %d, %Y')

class DiscussionTopic(models.Model):
    """
    A topic (thread) associated with a CourseOffering
    """
    offering = models.ForeignKey(CourseOffering, null=False)
    title = models.CharField(max_length=140, help_text="A brief description of the topic")
    content = models.TextField(help_text="The inital message for the topic")
    last_activity_at = models.DateTimeField(auto_now_add=True)
    message_count = models.IntegerField(default=0)
    status = models.CharField(max_length=3, choices=TOPIC_STATUSES, default='OPN')
    pinned = models.BooleanField()
    author = models.ForeignKey(Member)
    config = JSONField(null=False, blank=False, default={})
    
    def save(self, *args, **kwargs):
        if self.status not in [status[0] for status in TOPIC_STATUSES]:
            raise ValueError('Invalid topic status')
        super(DiscussionTopic, self).save(*args, **kwargs)
        
    def new_message_update(self):
        self.last_activity_at = datetime.datetime.now()
        self.message_count = self.message_count + 1
        self.save()
        
    def message_hidden_update(self):
        self.message_count = self.message_count - 1
        self.save()
        
    def message_visible_update(self):
        self.message_count = self.message_count + 1
        self.save()
        
    def last_activity_at_delta(self):
        return _time_delta_to_string(self.last_activity_at)
        
    def __unicode___(self):
        return self.title

MESSAGE_STATUSES = (
                  ('VIS', 'Visible'),
                  ('HID', 'Hidden'),
                  )

class DiscussionMessage(models.Model):
    """
    A message (post) associated with a Discussion Topic
    """
    topic = models.ForeignKey(DiscussionTopic)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=3, choices=MESSAGE_STATUSES, default='VIS')
    author = models.ForeignKey(Member)
    config = JSONField(null=False, blank=False, default={})
    
    def save(self, *args, **kwargs):
        if self.status not in [status[0] for status in MESSAGE_STATUSES]:
            raise ValueError('Invalid topic status')
        if not self.pk:
            self.topic.new_message_update()
        super(DiscussionMessage, self).save(*args, **kwargs)
