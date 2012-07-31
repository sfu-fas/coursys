from coredata.models import Member, CourseOffering
from django.db import models
from jsonfield.fields import JSONField
from courselib.json_fields import getter_setter
from pages.models import ParserFor, brushes_used
from django.utils.safestring import mark_safe
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
    offering = models.ForeignKey(CourseOffering, null=False)
    title = models.CharField(max_length=140, help_text="A brief description of the topic")
    content = models.TextField(help_text='The inital message for the topic, <a href="http://wikicreole.org/wiki/CheatSheet">WikiCreole-formatted</a>')
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now_add=True)
    message_count = models.IntegerField(default=0)
    status = models.CharField(max_length=3, choices=TOPIC_STATUSES, default='OPN', help_text="The topic status: Closed: no replies allowed, Hidden: cannot be seen")
    pinned = models.BooleanField(help_text="Should this topic be pinned to bring attention?")
    author = models.ForeignKey(Member)
    config = JSONField(null=False, blank=False, default={})
        # p.config['math']: content uses MathJax? (boolean)
        # p.config['brushes']: used SyntaxHighlighter brushes (list of strings)
    
    defaults = {'math': False, 'brushes': []}
    math, set_math = getter_setter('math')
    brushes, set_brushes = getter_setter('brushes')
    
    def save(self, *args, **kwargs):
        if self.status not in [status[0] for status in TOPIC_STATUSES]:
            raise ValueError('Invalid topic status')

        # update the metainfo about creole display        
        self.get_creole()
        brushes = brushes_used(self.Creole.parser.parse(self.content))
        self.set_brushes(list(brushes))
        # TODO: nobody sets config.math to True, but it is honoured if it is set magically. UI for that?
        
        super(DiscussionTopic, self).save(*args, **kwargs)
        
    def new_message_update(self):
        self.last_activity_at = datetime.datetime.now()
        self.message_count = self.message_count + 1
        self.save()
        
    def last_activity_at_delta(self):
        return _time_delta_to_string(self.last_activity_at)
    
    def created_at_delta(self):
        return _time_delta_to_string(self.created_at)
        
    def __unicode___(self):
        return self.title
    
    def __init__(self, *args, **kwargs):
        super(DiscussionTopic, self).__init__(*args, **kwargs)
        self.Creole = None
    
    def get_creole(self):
        "Only build the creole parser on-demand."
        if not self.Creole:
            self.Creole = ParserFor(self.offering)
        return self.Creole

    def html_content(self):
        "Convert self.content to HTML"
        creole = self.get_creole()
        html = creole.text2html(self.content)
        return mark_safe(html)
    
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

MESSAGE_STATUSES = (
                  ('VIS', 'Visible'),
                  ('HID', 'Hidden'),
                  )

class DiscussionMessage(models.Model):
    """
    A message (post) associated with a Discussion Topic
    """
    topic = models.ForeignKey(DiscussionTopic)
    content = models.TextField(blank=False, help_text=mark_safe('Reply to topic, <a href="http://wikicreole.org/wiki/CheatSheet">WikiCreole-formatted</a>'))
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=3, choices=MESSAGE_STATUSES, default='VIS')
    author = models.ForeignKey(Member)
    config = JSONField(null=False, blank=False, default={})
        # p.config['math']: content uses MathJax? (boolean)
        # p.config['brushes']: used SyntaxHighlighter brushes (list of strings)
    
    defaults = {'math': False, 'brushes': []}
    math, set_math = getter_setter('math')
    brushes, set_brushes = getter_setter('brushes')

    def save(self, *args, **kwargs):
        if self.status not in [status[0] for status in MESSAGE_STATUSES]:
            raise ValueError('Invalid topic status')
        if not self.pk:
            self.topic.new_message_update()

        # update the metainfo about creole display        
        self.topic.get_creole()
        brushes = brushes_used(self.topic.Creole.parser.parse(self.content))
        self.set_brushes(list(brushes))
        
        super(DiscussionMessage, self).save(*args, **kwargs)

    def html_content(self):
        "Convert self.content to HTML"
        creole = self.topic.get_creole()
        html = creole.text2html(self.content)
        return mark_safe(html)
    
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
    