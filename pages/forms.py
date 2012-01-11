from django import forms
from django.db import transaction
from pages.models import Page, PageVersion

class WikiField(forms.CharField):
    def __init__(self, *args, **kwargs):
        self.widget = forms.Textarea(attrs={'cols': 80, 'rows': 20})
        if 'help_text' not in kwargs:
            kwargs['help_text'] = 'Page formatted in <a href="http://www.wikicreole.org/wiki/AllMarkup">WikiCreole markup</a>.'
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
    def __init__(self, offering, *args, **kwargs):
        super(EditPageFileForm, self).__init__(*args, **kwargs)
        # force the right course offering into place
        self.offering = offering
        self.fields['offering'].initial = offering.id
        
        # existing data for other fields
        if self.instance.id:
            self.initial['wikitext'] = self.instance.current_version().wikitext
            self.initial['math'] = self.instance.current_version().math()
        
        # tidy up ACL choices: remove NONE
        self.fields['can_read'].choices = [(v,l) for (v,l) in self.fields['can_read'].choices
                                           if v != 'NONE']
        self.fields['can_write'].choices = [(v,l) for (v,l) in self.fields['can_write'].choices
                                           if v != 'NONE']


    def clean_offering(self):
        if self.cleaned_data['offering'] != self.offering:
            raise forms.ValidationError("Wrong course offering.")
        return self.cleaned_data['offering']

    class Meta:
        model = Page
        exclude = ('slug', 'config')
        widgets = {
            'offering': forms.HiddenInput(),
            'title': forms.TextInput(attrs={'size':50}),
            'label': forms.TextInput(attrs={'size':20}),
        }



class EditPageForm(EditPageFileForm):
    wikitext = WikiField()
    comment = CommentField()
    
    math = forms.BooleanField(required=False, help_text='Will this page use <a href="http://www.mathjax.org/">MathJax</a> for formulas?')

    def save(self, editor, *args, **kwargs):
        # also create the PageVersion object.
        wikitext = self.cleaned_data['wikitext']
        comment = self.cleaned_data['comment']
        pv = PageVersion(wikitext=wikitext, comment=comment, editor=editor)
        # set config data
        pv.set_math(self.cleaned_data['math'])

        self.instance.offering = self.offering
        super(EditPageForm, self).save(*args, **kwargs)
        pv.page=self.instance
        pv.save()


class EditFileForm(EditPageFileForm):
    file_attachment = forms.FileField(label="File")

    def save(self, editor, *args, **kwargs):
        # also create the PageVersion object.
        upfile = self.cleaned_data['file_attachment']
        pv = PageVersion(file_attachment=upfile, file_mediatype=upfile.content_type,
                         file_name=upfile.name, editor=editor)

        self.instance.offering = self.offering
        super(EditFileForm, self).save(*args, **kwargs)
        pv.page=self.instance
        pv.save()

