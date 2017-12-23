from discuss.models import DiscussionTopic, DiscussionMessage, DiscussionSubscription, TopicSubscription
from django import forms
from django.forms.widgets import TextInput
from courselib.markup import MarkupContentField, MarkupContentMixin
import genshi


TOPIC_CHOICES_STAFF = (
                      ('OPN', 'Open'),
                      ('CLO', 'Closed'),
                      )


def discussion_topic_form_factory(view_type, data=None, instance=None):
    """
    Return the current form for a discussion topic based on the view_type (student/staff)
    """
    if view_type == 'student':
        return _DiscussionTopicForm(data=data, instance=instance)
    elif view_type == 'staff':
        return _DiscussionTopicFormStaff(data=data, instance=instance)
    else:
        raise ValueError()


def _tag_set(parse):
    """
    All tags used in the HTML conversion of the content
    """
    res = set()
    if hasattr(parse, 'children'):
        # recurse on child elements
        for c in parse.children:
            res |= _tag_set(c)

    if isinstance(parse, genshi.builder.Element):
        # add this tag
        res.add(str(parse.tag))
    
    return res


class _DiscussionTopicForm(MarkupContentMixin(field_name='content'), forms.ModelForm):
    title = forms.CharField(widget=TextInput(attrs={'size': 60}), help_text="What is this topic about?")
    content = MarkupContentField(label='Content', with_wysiwyg=True, restricted=True, rows=10)

    class Meta:
        model = DiscussionTopic
        exclude = ('offering', 'last_activity_at', 'created_at', 'message_count', 'author', 'config', 'status', 'pinned')


class _DiscussionTopicFormStaff(_DiscussionTopicForm):
    class Meta(_DiscussionTopicForm.Meta):
        exclude = ('offering', 'last_activity_at', 'created_at', 'message_count', 'author', 'config')


class DiscussionTopicStatusForm(forms.ModelForm):
    class Meta:
        model = DiscussionTopic
        exclude = ('title', 'content', 'offering', 'last_activity_at', 'message_count', 'author', 'config')


class DiscussionMessageForm(MarkupContentMixin(field_name='content'), forms.ModelForm):
    content = MarkupContentField(label='Content', with_wysiwyg=True, restricted=True, rows=10)
    class Meta:
        model = DiscussionMessage
        exclude = ('topic', 'created_at', 'modified_at', 'status', 'author', 'config')


class DiscussionSubscriptionForm(forms.ModelForm):
    class Meta:
        model = DiscussionSubscription
        exclude = ('member',)


class TopicSubscriptionForm(forms.ModelForm):
    class Meta:
        model = TopicSubscription
        exclude = ('member','topic')
