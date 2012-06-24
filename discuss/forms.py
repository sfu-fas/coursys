from discuss.models import DiscussionTopic, DiscussionMessage
from django import forms
from django.forms.widgets import Textarea, TextInput

TOPIC_CHOICES_STAFF = (
                      ('OPN', 'Open'),
                      ('CLO', 'Closed'),
                      )

def discussion_topic_form_factory(view_type, post_data=None, instance=None):
    """
    Return the current form for a discussion topic based on the view_type (student/staff)
    """
    if view_type == 'student':
        return _DiscussionTopicForm(post_data, instance=instance)
    elif view_type == 'staff':
        return _DiscussionTopicFormStaff(post_data, instance=instance)
    else:
        raise ValueError()

            
class _DiscussionTopicForm(forms.ModelForm):
    title = forms.CharField(widget=TextInput(attrs={'size': 60}), help_text="What is this topic about?") 
    class Meta:
        model = DiscussionTopic
        exclude = ('offering', 'last_activity_at', 'created_at', 'message_count', 'author', 'config', 'status', 'pinned')
        widgets = {
                   'content': Textarea(attrs={'cols': 70, 'rows': 20}),
                   }
        
class _DiscussionTopicFormStaff(_DiscussionTopicForm):
    class Meta(_DiscussionTopicForm.Meta):
        exclude = ('offering', 'last_activity_at', 'created_at', 'message_count', 'author', 'config')
                   
            
class DiscussionTopicStatusForm(forms.ModelForm):
    class Meta:
        model = DiscussionTopic
        exclude = ('title', 'content', 'offering', 'last_activity_at', 'message_count', 'author', 'config')
        
class DiscussionMessageForm(forms.ModelForm):
    class Meta:
        model = DiscussionMessage
        exclude = ('topic', 'created_at', 'modified_at', 'status', 'author', 'config')
    
