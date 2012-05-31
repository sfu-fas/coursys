from coredata.models import CourseOffering, Member
from django.db import models
from jsonfield.fields import JSONField
import datetime

class Discussion(models.Model):
    """
    A discussion(forum) for a course offering
    """
    course_offering = models.ForeignKey(CourseOffering, unique=True)
    allow_discussion = models.BooleanField(default=False)
    config = JSONField(null=False, blank=False, default=True)


TOPIC_STATUSES = (
                  ('OP', 'Open'),
                  ('ANS', 'Answered'),
                  ('HID', 'Hidden'),
                  )

class DiscussionTopic(models.Model):
    """
    A topic(thread) associated with a Discussion
    """
    title = models.CharField(max_length=30, help_text="The name of the topic that others will see")
    created_at = models.DateTimeField(auto_now_add=True)
    last_post_at = models.DateTimeField(null=True)
    discussion = models.ForeignKey(Discussion)
    status = models.CharField(max_length=3, choices=TOPIC_STATUSES)
    config = JSONField(null=False, blank=False, default=True)
    
    def save(self, *args, **kwargs):
        if self.status not in [status[0] for status in TOPIC_STATUSES]:
            raise ValueError('Invalid topic status')
        super(DiscussionTopic, self).save(*args, **kwargs)
        
    def update_last_post(self):
        self.last_post_at = datetime.datetime.now()
        self.save()
        
    def __unicode___(self):
        return self.title


class DiscussionMessage(models.Model):
    """
    A message(post) associated with a Discussion Topic
    """
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    hidden = models.BooleanField(default=False, help_text="Should this message be hidden from students?")
    topic = models.ForeignKey(DiscussionTopic)
    author = models.ForeignKey(Member)
    config = JSONField(null=False, blank=False, default=True)
    
    def save(self, *args, **kwargs):
        if not self.pk:
            self.topic.update_last_post()
        super(DiscussionMessage, self).save(*args, **kwargs)
