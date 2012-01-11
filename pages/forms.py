from django import forms
from pages.models import Page, PageVersion

class WikiField(forms.CharField):
    def __init__(self, *args, **kwargs):
        self.widget = forms.Textarea(attrs={'cols': 80, 'rows': 20})
        super(WikiField, self).__init__(*args, **kwargs)

class CommentField(forms.CharField):
    def __init__(self, *args, **kwargs):
        self.widget = forms.TextInput(attrs={'size': 60})
        if 'required' not in kwargs:
            kwargs['required'] = False
        if 'help_text' not in kwargs:
            kwargs['help_text'] = 'Comment on this change'
        super(CommentField, self).__init__(*args, **kwargs)

class EditPageForm(forms.ModelForm):
    wikitext = WikiField()
    comment = CommentField()
    
    math = forms.BooleanField(required=False, help_text='Will this page use <a href="http://www.mathjax.org/">MathJax</a> for formulas?')
    
    def __init__(self, offering, *args, **kwargs):
        super(EditPageForm, self).__init__(*args, **kwargs)
        # force the right course offering into place
        self.offering = offering
        self.fields['offering'].initial = offering.id
        
        # existing data for other fields
        if self.instance.id:
            self.initial['wikitext'] = self.instance.current_version().wikitext
            self.initial['math'] = self.instance.math()
        
        # tidy up ACL choices: remove NONE
        self.fields['can_read'].choices = [(v,l) for (v,l) in self.fields['can_read'].choices
                                           if v != 'NONE']
        self.fields['can_write'].choices = [(v,l) for (v,l) in self.fields['can_write'].choices
                                           if v != 'NONE']

    def clean_offering(self):
        if self.cleaned_data['offering'] != self.offering:
            raise forms.ValidationError("Wrong course offering.")
        return self.cleaned_data['offering']

    def save(self, editor, *args, **kwargs):
        # set config data
        self.instance.set_math(self.cleaned_data['math'])
        
        # also create the PageVersion object.
        wikitext = self.cleaned_data['wikitext']
        comment = self.cleaned_data['comment']
        pv = PageVersion(wikitext=wikitext, comment=comment, editor=editor)

        self.instance.offering = self.offering
        super(EditPageForm, self).save(*args, **kwargs)
        pv.page=self.instance
        pv.save()

    class Meta:
        model = Page
        exclude = ('slug', 'config')
        widgets = {
            'offering': forms.HiddenInput(),
            'title': forms.TextInput(attrs={'size':50}),
            'label': forms.TextInput(attrs={'size':20}),
        }
