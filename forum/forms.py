from django import forms
from django.utils.html import escape
from django.utils.safestring import mark_safe

from coredata.models import Member
from courselib.markup import MarkupContentMixin, MarkupContentField
from forum import DEFAULT_FORUM_MARKUP
from forum.models import Post, Identity, THREAD_PRIVACY_CHOICES, AVATAR_TYPE_CHOICES


class _PostForm(MarkupContentMixin(field_name='content'), forms.ModelForm):
    content = MarkupContentField(label='Post', default_markup=DEFAULT_FORUM_MARKUP, with_wysiwyg=True, restricted=True, rows=10)
    identity = forms.ChoiceField(choices=[], initial='NAME', widget=forms.RadioSelect)  # choices filled by __init__

    class Meta:
        model = Post
        fields = ()
        widgets = {
            'type': forms.RadioSelect,
        }

    def __init__(self, offering_identity: str, member: Member, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['identity'].choices = Identity.identity_choices(offering_identity, member)

    def save(self, *args, **kwargs):
        self.instance.identity = self.cleaned_data['identity']
        return super().save(*args, **kwargs)


class ThreadForm(_PostForm):
    title = forms.CharField(label="Title")
    privacy = forms.ChoiceField(choices=THREAD_PRIVACY_CHOICES, initial='ALL', widget=forms.RadioSelect)

    class Meta(_PostForm.Meta):
        fields = ('title', 'type', 'identity', 'privacy', 'content')

    def clean(self):
        cleaned_data = super().clean()
        identity = cleaned_data.get('identity')
        privacy = cleaned_data.get('privacy')
        if identity == 'ANON' and privacy == 'I':
            self.add_error('identity', 'Private questions cannot be anonymous.')


class ReplyForm(_PostForm):
    class Meta(_PostForm.Meta):
        fields = ('identity', 'content')


class SearchForm(forms.Form):
    q = forms.CharField(label='Search posts')


class AvatarForm(forms.Form):
    avatar_type = forms.ChoiceField(label='Avatar type', choices=AVATAR_TYPE_CHOICES, widget=forms.RadioSelect,
                                    help_text='Avatar image used when you post non-anonymously')
    anon_avatar_type = forms.ChoiceField(label='Anonymous avatar type', choices=AVATAR_TYPE_CHOICES, widget=forms.RadioSelect,
                                    help_text='Avatar image used when you post anonymously')

    def __init__(self, identity: Identity, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.initial['avatar_type'] = identity.avatar_type
        self.initial['anon_avatar_type'] = identity.anon_avatar_type

        choices = [
            (
                value,
                mark_safe(escape(descr) + ' <img src="' + escape(identity.avatar_image_url(avatar_type=value, anon=False))
                    + '" alt="" class="avatar" loading="lazy" referrerpolicy="no-referrer" />')
            )
            for value, descr in self.fields['avatar_type'].choices
        ]
        self.fields['avatar_type'].choices = choices

        choices = [
            (
                value,
                mark_safe(escape(descr) + ' <img src="' + escape(identity.avatar_image_url(avatar_type=value, anon=True))
                    + '" alt="" class="avatar" loading="lazy" referrerpolicy="no-referrer" />')
            )
            for value, descr in self.fields['anon_avatar_type'].choices
            if value != 'gravatar'
        ]
        self.fields['anon_avatar_type'].choices = choices
