from django import forms

from coredata.models import Member
from courselib.markup import MarkupContentMixin, MarkupContentField
from forum import DEFAULT_FORUM_MARKUP
from forum.models import Thread, Post, AnonymousIdentity, Reply


class ThreadForm(MarkupContentMixin(field_name='content'), forms.ModelForm):
    title = forms.CharField(label="Title")
    content = MarkupContentField(label='Post', default_markup=DEFAULT_FORUM_MARKUP, with_wysiwyg=True, restricted=True, rows=10)
    identity = forms.ChoiceField(choices=[], initial='NAME', widget=forms.RadioSelect)  # choices filled by __init__

    class Meta:
        model = Post
        fields = ('title', 'type', 'identity', 'content')
        widgets = {
            'type': forms.RadioSelect,
        }

    def __init__(self, offering_identity: str, member: Member, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['identity'].choices = AnonymousIdentity.identity_choices(offering_identity, member)

    def save(self, *args, **kwargs):
        self.instance.identity = self.cleaned_data['identity']
        return super().save(*args, **kwargs)


class ReplyForm(MarkupContentMixin(field_name='content'), forms.ModelForm):
    content = MarkupContentField(label='Post', default_markup=DEFAULT_FORUM_MARKUP, with_wysiwyg=True, restricted=True, rows=10)
    identity = forms.ChoiceField(choices=[], initial='NAME', widget=forms.RadioSelect)  # choices filled by __init__

    class Meta:
        model = Post
        fields = ('identity', 'content')
        widgets = {
        }

    def __init__(self, offering_identity: str, member: Member, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['identity'].choices = AnonymousIdentity.identity_choices(offering_identity, member)

    def save(self, *args, **kwargs):
        self.instance.identity = self.cleaned_data['identity']
        return super().save(*args, **kwargs)
