from django import forms
from django.db import transaction

from coredata.models import Person
from pages.models import Page, PageVersion, PagePermission, PERMISSION_ACL_CHOICES
from courselib.markup import MarkupContentField, MarkupContentMixin


class WikiField(forms.CharField):
    # TODO: search and destroy other usages
    def __init__(self, *args, **kwargs):
        self.widget = forms.Textarea(attrs={'cols': 70, 'rows': 20})
        if 'help_text' not in kwargs:
            kwargs['help_text'] = 'Page formatted in <a href="/docs/pages">WikiCreole markup</a>.'  # hard-coded URL since this is evaluated before urls.py: could be reverse_lazy?
        super(WikiField, self).__init__(*args, **kwargs)


class CommentField(forms.CharField):
    def __init__(self, *args, **kwargs):
        self.widget = forms.TextInput(attrs={'size': 60})
        if 'required' not in kwargs:
            kwargs['required'] = False
        if 'help_text' not in kwargs:
            kwargs['help_text'] = 'Comment on this change'
        super(CommentField, self).__init__(*args, **kwargs)


class EditPageFileForm(forms.ModelForm):
    releasedate = forms.DateField(initial=None, required=False, label="Release Date",
                help_text='Date the "can read" permissions take effect. Leave blank for no timed-release. Pages can always be viewed by instructors and TAs.')
    # disabling editing-release UI on the basis that probably nobody needs it
    #editdate = forms.DateField(initial=None, required=False, label="Editable Date",
    #            help_text='Date the "can change" permissions take effect. Leave blank for no timed-release. Pages can always be edited by instructors and TAs.')
    def __init__(self, offering, *args, **kwargs):
        super(EditPageFileForm, self).__init__(*args, **kwargs)
        # force the right course offering into place
        self.offering = offering
        self.fields['offering'].initial = offering.id
        
        # existing data for other fields
        if self.instance.id:
            version = self.instance.current_version()
            self.initial['title'] = version.title
            #self.initial['markup_content'] = [version.wikitext, version.markup(), version.math()]
            self.initial['releasedate'] = self.instance.releasedate()
            self.initial['editdate'] = self.instance.editdate()
        
        # tidy up ACL choices: remove NONE
        self.fields['can_read'].choices = [(v,l) for (v,l) in self.fields['can_read'].choices
                                           if v != 'NONE']
        self.fields['can_write'].choices = [(v,l) for (v,l) in self.fields['can_write'].choices
                                           if v != 'NONE']


    def clean_offering(self):
        if self.cleaned_data['offering'] != self.offering:
            raise forms.ValidationError("Wrong course offering.")
        return self.cleaned_data['offering']

    @transaction.atomic
    def clean_label(self):
        label = self.cleaned_data['label']
        error = self.instance.label_okay(label)
        if error:
            raise forms.ValidationError(error)

        otherpages = Page.objects.filter(label=label, offering=self.offering)
        if self.instance:
            otherpages = otherpages.exclude(id=self.instance.id)
        if otherpages.exists():
            raise forms.ValidationError('A page with that label already exists')

        return label

    class Meta:
        model = Page
        exclude = ('config',)
        widgets = {
            'offering': forms.HiddenInput(),
            'title': forms.TextInput(attrs={'size':50}),
            'label': forms.TextInput(attrs={'size':20}),
        }


class EditPageForm(MarkupContentMixin(field_name='markup_content'), EditPageFileForm):
    title = forms.CharField(max_length=60, widget=forms.TextInput(attrs={'size':50}))
    markup_content = MarkupContentField(label='Content', with_wysiwyg=True)
    comment = CommentField()

    def __init__(self, instance=None, *args, **kwargs):
        if instance:
            # push the initial values into the page object, to make MarkupContentMixin happy
            version = instance.current_version()
            instance.markup_content = version.wikitext
            instance.markup = version.markup()
            instance.math = version.math()
        super(EditPageForm, self).__init__(instance=instance, *args, **kwargs)

    @transaction.atomic
    def save(self, editor, *args, **kwargs):
        # create the PageVersion object: distribute the self.cleaned_data values appropriately
        wikitext = self.cleaned_data['markup_content']
        comment = self.cleaned_data['comment']
        title = self.cleaned_data['title']
        pv = PageVersion(title=title, wikitext=wikitext, comment=comment, editor=editor)
        pv.set_markup(self.cleaned_data['_markup'])
        pv.set_math(self.cleaned_data['_math'])

        self.instance.offering = self.offering
        pg = super(EditPageForm, self).save(*args, **kwargs)
        pv.page=self.instance
        pv.save()
        return pg


class EditPageFormRestricted(EditPageForm):
    """
    Restricted version of EditPageForm for students.
    """
    def __init__(self, *args, **kwargs):
        super(EditPageFormRestricted, self).__init__(*args, **kwargs)
        if self.instance.label:
            # can't change label, but can set for a new page
            del self.fields['label']
        del self.fields['can_write']
        if 'releasedate' in self.fields:
            del self.fields['releasedate']
        if 'editdate' in self.fields:
            del self.fields['editdate']

EditPageForm.restricted_form = EditPageFormRestricted


class EditFileForm(EditPageFileForm):
    file_attachment = forms.FileField(label="File")

    @transaction.atomic
    def save(self, editor, *args, **kwargs):
        # also create the PageVersion object.
        upfile = self.cleaned_data['file_attachment']
        pv = PageVersion(file_attachment=upfile, file_mediatype=upfile.content_type,
                         file_name=upfile.name, editor=editor)

        self.instance.offering = self.offering
        pg = super(EditFileForm, self).save(*args, **kwargs)
        pv.page=self.instance
        pv.save()
        return pg

class EditFileFormRestricted(EditFileForm):
    """
    Restricted version of EditFileForm for students.
    """
    def __init__(self, *args, **kwargs):
        super(EditFileFormRestricted, self).__init__(*args, **kwargs)
        if self.instance.label:
            # can't change label, but can set for a new page
            del self.fields['label']
        del self.fields['can_write']


EditFileForm.restricted_form = EditFileFormRestricted


PERSON_ACL_CHOICES = [
    ('STAF', 'TA-equivalent'),
    ('STUD', 'student-equivalent')
]

class PermissionForm(forms.Form):
    person = forms.CharField(required=True, label="Username", max_length=8,
                             help_text="The person's SFU username. Must be the ID they use to log in, not an email alias.",
                             widget=forms.TextInput(attrs={'size': '9'}))
    role = forms.ChoiceField(required=True, label="Role", choices=PERSON_ACL_CHOICES, initial='STUD')

    def clean_person(self) -> Person:
        userid = self.cleaned_data['person']
        try:
            person = Person.objects.get(userid=userid)
        except Person.DoesNotExist:
            raise forms.ValidationError('That username does not exist')
        return person
