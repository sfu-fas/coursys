from coredata.models import CourseOffering, Member
from django.db import models
from jsonfield.fields import JSONField
import datetime

TOPIC_STATUSES = (
                  ('OPN', 'Open'),
                  ('ANS', 'Answered'),
                  ('HID', 'Hidden'),
                  )

class DiscussionTopic(models.Model):
    """
    A topic (thread) associated with a CourseOffering
    """
    offering = models.ForeignKey(CourseOffering, null=False)
    title = models.CharField(max_length=140, help_text="The name of the topic that others will see")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    last_post_at = models.DateTimeField(null=True)
    status = models.CharField(max_length=3, choices=TOPIC_STATUSES)
    author = models.ForeignKey(Member)
    config = JSONField(null=False, blank=False, default={})
    
    def save(self, *args, **kwargs):
        if self.status not in [status[0] for status in TOPIC_STATUSES]:
            raise ValueError('Invalid topic status')
        super(DiscussionTopic, self).save(*args, **kwargs)
        
    def update_last_post(self):
        self.last_post_at = datetime.datetime.now()
        self.save()
        
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
    status = models.CharField(max_length=3, choices=MESSAGE_STATUSES)
    author = models.ForeignKey(Member)
    config = JSONField(null=False, blank=False, default={})
    
    def save(self, *args, **kwargs):
        if self.status not in [status[0] for status in MESSAGE_STATUSES]:
            raise ValueError('Invalid topic status')
        if not self.pk:
            self.topic.update_last_post()
        super(DiscussionMessage, self).save(*args, **kwargs)
