from django import forms
from django.urls import reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe

from coredata.models import Member
from courselib.markup import MarkupContentMixin, MarkupContentField
from forum import DEFAULT_FORUM_MARKUP
from forum.models import Post, Identity, THREAD_PRIVACY_CHOICES, AVATAR_TYPE_CHOICES, DIGEST_FREQUENCY_CHOICES


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
        if 'identity' in self.fields:
            self.fields['identity'].choices = Identity.identity_choices(offering_identity, member)
            ident_url = reverse('offering:forum:identity', kwargs={'course_slug': member.offering.slug})
            self.fields['identity'].help_text = mark_safe('See <a href="%s">discussion forum identities</a> for more information.' % (ident_url,))

    def save(self, *args, **kwargs):
        if 'identity' in self.fields:
            self.instance.identity = self.cleaned_data['identity']
        return super().save(*args, **kwargs)


class ThreadForm(_PostForm):
    title = forms.CharField(label="Title")
    privacy = forms.ChoiceField(choices=THREAD_PRIVACY_CHOICES, initial='ALL', widget=forms.RadioSelect)

    class Meta(_PostForm.Meta):
        fields = ('title', 'type', 'identity', 'privacy', 'content')

    def clean(self):
        cleaned_data = super().clean()
        if 'identity' in self.fields:
            identity = cleaned_data.get('identity')
            privacy = cleaned_data.get('privacy')
            if identity == 'ANON' and privacy == 'I':
                self.add_error('identity', 'Private questions cannot be anonymous.')


class InstrEditThreadForm(ThreadForm):
    # instructors can't see/edit anonymity setting when editing student posts
    identity = None

    class Meta(ThreadForm.Meta):
        fields = ('title', 'type', 'privacy', 'content')


class InstrThreadForm(InstrEditThreadForm):
    broadcast_announcement = forms.BooleanField(required=False, help_text='This will cause the post to be emailed '
        'directly to students in the course and pin the post (until you un-pin it). We ask instructors to use this sparingly.')

    # instructors can't post anonymously
    def save(self, commit=True, *args, **kwargs):
        res = super().save(commit=False, *args, **kwargs)
        self.instance.identity = 'NAME'
        if commit:
            res.save()
        return res

    def clean(self):
        super().clean()
        broadcast_announcement = self.cleaned_data.get('broadcast_announcement')
        privacy = self.cleaned_data.get('privacy')
        if broadcast_announcement and privacy != 'ALL':
            self.add_error('broadcast_announcement', 'You cannot broadcast a private thread: it must be visible to students to broadcast as an announcement.')


class ReplyForm(_PostForm):
    class Meta(_PostForm.Meta):
        fields = ('identity', 'content')


class InstrEditReplyForm(ReplyForm):
    # instructors can't see/edit anonymity setting when editing student posts
    identity = None

    class Meta(ReplyForm.Meta):
        fields = ('content',)


class InstrReplyForm(InstrEditReplyForm):
    # instructors can't post anonymously
    def save(self, commit=True, *args, **kwargs):
        res = super().save(commit=False, *args, **kwargs)
        self.instance.identity = 'NAME'
        if commit:
            res.save()
        return res


class SearchForm(forms.Form):
    q = forms.CharField(label='Search posts')


class PseudonymForm(forms.Form):
    form = forms.CharField(initial='pseudonym', widget=forms.HiddenInput)


class AvatarForm(forms.Form):
    form = forms.CharField(initial='avatar', widget=forms.HiddenInput)
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


DIGEST_CHOICES = [(0, 'never: no digest emails')] + DIGEST_FREQUENCY_CHOICES


class DigestForm(forms.Form):
    digest_frequency = forms.ChoiceField(label='Digest Email Frequency', choices=DIGEST_CHOICES,
                                         widget=forms.RadioSelect,
                                         help_text='How often would you like to receive digests of forum activity?')
