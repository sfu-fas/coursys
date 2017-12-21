from discuss.models import DiscussionTopic, DiscussionMessage, DiscussionSubscription, TopicSubscription
from django import forms
from django.forms.widgets import Textarea, TextInput
from courselib.markup import MarkupContentField
import genshi


TOPIC_CHOICES_STAFF = (
                      ('OPN', 'Open'),
                      ('CLO', 'Closed'),
                      )


def discussion_topic_form_factory(view_type, creole, data=None, instance=None):
    """
    Return the current form for a discussion topic based on the view_type (student/staff)
    """
    if view_type == 'student':
        return _DiscussionTopicForm(data, creole=creole, instance=instance)
    elif view_type == 'staff':
        return _DiscussionTopicFormStaff(data, creole=creole, instance=instance)
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


def _creole_content_okay(creole, content):
    """
    Use this Creole parser to check this content: make sure only allowed tags are used
    (to prevent format-bombing discussions).
    
    Raises ValidationErrors if not.
    """
    parsed_content = creole.parser.parse(content)
    tags = _tag_set(parsed_content)
    if 'h1' in tags or 'h2' in tags:
        raise forms.ValidationError("Cannot use level 1 (=) or 2 (==) headings in discussions.")
    if 'hr' in tags:
        raise forms.ValidationError("Cannot use horizontal rules (----) in discussions).")
    if 'img' in tags:
        raise forms.ValidationError("Cannot use images ({{...}}) in discussions).")


class _DiscussionTopicForm(forms.ModelForm):
    title = forms.CharField(widget=TextInput(attrs={'size': 60}), help_text="What is this topic about?")
    content = MarkupContentField(label='Content', with_wysiwyg=True, rows=10)

    class Meta:
        model = DiscussionTopic
        exclude = ('offering', 'last_activity_at', 'created_at', 'message_count', 'author', 'config', 'status', 'pinned')
    
    def __init__(self, data, creole, instance=None, *args, **kwargs):
        # creole can be None if no validation will happen with this instance.
        super(_DiscussionTopicForm, self).__init__(data, instance=instance, *args, **kwargs)
        if instance:
            self.initial['content'] = [instance.content, instance.markup(), instance.math()]
        else:
            self.initial['content'] = ['', 'creole', False]
        self.creole = creole

    def save(self, commit=True, *args, **kwargs):
        content, markup, math = self.cleaned_data['content']
        t = super(_DiscussionTopicForm, self).save(commit=False, *args, **kwargs)
        t.content = content
        t.set_markup(markup)
        t.set_math(math)
        if commit:
            t.save()
        return t


class _DiscussionTopicFormStaff(_DiscussionTopicForm):
    class Meta(_DiscussionTopicForm.Meta):
        exclude = ('offering', 'last_activity_at', 'created_at', 'message_count', 'author', 'config')


class DiscussionTopicStatusForm(forms.ModelForm):
    class Meta:
        model = DiscussionTopic
        exclude = ('title', 'content', 'offering', 'last_activity_at', 'message_count', 'author', 'config')


class DiscussionMessageForm(forms.ModelForm):
    content = MarkupContentField(label='Content', with_wysiwyg=True, rows=10)
    class Meta:
        model = DiscussionMessage
        exclude = ('topic', 'created_at', 'modified_at', 'status', 'author', 'config')

    def __init__(self, creole, instance=None, *args, **kwargs):
        # creole can be None if no validation will happen with this instance.
        super(DiscussionMessageForm, self).__init__(instance=instance, *args, **kwargs)
        if instance:
            self.initial['content'] = [instance.content, instance.markup(), instance.math()]
        else:
            self.initial['content'] = ['', 'creole', False]
        self.creole = creole

    def save(self, commit=True, *args, **kwargs):
        content, markup, math = self.cleaned_data['content']
        m = super(DiscussionMessageForm, self).save(commit=False, *args, **kwargs)
        m.content = content
        m.set_markup(markup)
        m.set_math(math)
        if commit:
            m.save()
        return m


class DiscussionSubscriptionForm(forms.ModelForm):
    class Meta:
        model = DiscussionSubscription
        exclude = ('member',)


class TopicSubscriptionForm(forms.ModelForm):
    class Meta:
        model = TopicSubscription
        exclude = ('member','topic')
