from django import forms
from discuss.models import DiscussionTopic
from django.forms.widgets import Textarea, TextInput

TOPIC_CHOICES_STAFF = (
                      ('OPN', 'Open'),
                      ('CLO', 'Closed'),
                      )

class DiscussionTopicForm(forms.ModelForm):
    title = forms.CharField(min_length=15, widget=TextInput(attrs={'size': 60}), help_text="What is this topic about?")
    status = forms.ChoiceField(choices=TOPIC_CHOICES_STAFF, help_text="Can students post on this topic?")
    pinned = forms.BooleanField(required=False, help_text="Should this topic be pinned to bring attention?")
    class Meta:
        model = DiscussionTopic
        exclude = ('offering', 'last_activity_at', 'message_count', 'author', 'config')
        widgets = {
                   'content': Textarea(attrs={'cols': 80, 'rows': 30})
                   }
        
    def __init__(self, *args, **kwargs):
        view = None
        try:
            view = kwargs['discussion_view']
            del kwargs['discussion_view']
        except KeyError:
            pass
        super(DiscussionTopicForm, self).__init__(*args, **kwargs)
        if view is not 'staff':
            del self.fields['status']
            del self.fields['pinned']
