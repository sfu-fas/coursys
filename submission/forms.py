from django import forms
from submission.models import *
from django.forms.widgets import Textarea, TextInput, FileInput
from django.forms import ModelForm, URLField
from django.conf import settings
from django.utils.safestring import mark_safe
import urllib


_required_star = '<em><img src="'+settings.MEDIA_URL+'icons/required_star.gif" alt="required"/></em>'

class ComponentForm(ModelForm):
    #override title to have 'required star'
    title = forms.CharField(max_length=100, help_text='Name for this component (e.g. "Part 1" or "Programming Section")', label=mark_safe("Title"+_required_star))


class ArchiveComponentForm(ComponentForm):
    class Meta:
        model = ArchiveComponent
        fields = ['title', 'description', 'max_size', 'position']
        widgets = {
            'description': Textarea(attrs={'cols': 50, 'rows': 5}),
            'max_size': TextInput(attrs={'style':'width:5em'}),
            'position': TextInput(attrs={'maxlength':'3', 'style':'width:2em'}),
        }

class URLComponentForm(ComponentForm):
    class Meta:
        model = URLComponent
        fields = ['title', 'description', 'position']
        widgets = {
            'description': Textarea(attrs={'cols':50, 'rows':5}),
            'position': TextInput(attrs={'maxlength':'3', 'style':'width:2em'}),
        }

class CppComponentForm(ComponentForm):
    class Meta:
        model = CppComponent
        fields = ['title', 'description', 'position']
        widgets = {
            'description': Textarea(attrs={'cols':50, 'rows':5}),
            'position': TextInput(attrs={'maxlength':'3', 'style':'width:2em'}),
        }

class JavaComponentForm(ComponentForm):
    class Meta:
        model = JavaComponent
        fields = ['title', 'description', 'position']
        widgets = {
            'description': Textarea(attrs={'cols':50, 'rows':5}),
            'position': TextInput(attrs={'maxlength':'3', 'style':'width:2em'}),
        }

class PlainTextComponentForm(ComponentForm):
    class Meta:
        model = PlainTextComponent
        fields = ['title', 'description', 'max_length', 'position']
        widgets = {
            'description': Textarea(attrs={'cols':50, 'rows':5}),
            'max_length': TextInput(attrs={'style':'width:5em'}),
            'position': TextInput(attrs={'maxlength':'3', 'style':'width:2em'}),
        }

class SubmissionForm(ModelForm):
    class Meta:
        model = SubmittedComponent
        fields = []
        widgets = {}
    def check_type(self, file):
        print '!!!'
        print filetype(file).lower()
        print file.name[file.name.rfind('.'):].lower()
        if file.name[file.name.rfind('.'):].lower()!= filetype(file).lower():
            print "fail"
            return False
        for extension in self.component.extension:
            if extension.lower() == filetype(file).lower():
                
                return True
        return False
    def check_is_empty(self, data):
        if data == None:
            return True
        if len(data) == 0:
            return True
        return False


class SubmittedURLForm(SubmissionForm):
    class Meta:
        model = SubmittedURL
        fields = ['url']
        widgets = {
            'url': TextInput(attrs={'style':'width:25em'}),
        }
    def clean_url(self):
        url = self.cleaned_data['url']
        if self.check_is_empty(url):
            raise forms.ValidationError("No submission!")
        return url;

class SubmittedArchiveForm(SubmissionForm):
    class Meta:
        model = SubmittedArchive
        fields = ['archive']
        widgets = {'archive': FileInput()}
    def check_size(self, file):
        if file.size / 1024 > self.component.max_size:
            return False
        return True
    def clean_archive(self):
        data = self.cleaned_data['archive']
        if self.check_is_empty(data):
            raise forms.ValidationError("No submission!")
        if not self.check_type(data):
            raise forms.ValidationError('Type not match!')
        if not self.check_size(data):
            raise forms.ValidationError("File size exceeded max size, component can not be uploaded!")
        return data

class SubmittedCppForm(SubmissionForm):
    class Meta:
        model = SubmittedCpp
        fields = ['cpp']
        widgets = {'cpp': FileInput()}
    def clean_cpp(self):
        data = self.cleaned_data['cpp']
        if self.check_is_empty(data):
            raise forms.ValidationError("No submission!")
        if not self.check_type(data):
            raise forms.ValidationError("Type not match!")
        return data

class SubmittedJavaForm(SubmissionForm):
    class Meta:
        model = SubmittedJava
        fields = ['java']
        widgets = {'java':FileInput()}
    def clean_java(self):
        data = self.cleaned_data['java']
        if self.check_is_empty(data):
            raise forms.ValidationError("No submission!")
        if not self.check_type(data):
            raise forms.ValidationError("Type not match!")
        return data

class SubmittedPlainTextForm(SubmissionForm):
    class Meta:
        model = SubmittedPlainText
        fields = ['text']
        widgets = {'text':Textarea(attrs = {'cols':50, 'rows':5})}
    def check_length(self, text):
        if len(text) > self.component.max_length:
            return False
        return True
    def clean_text(self):
        data = self.cleaned_data['text']
        if self.check_is_empty(data):
            raise forms.ValidationError("No submission!")
        if not self.check_length(data):
            raise forms.ValidationError("Text Length exceeded max length, text can not be uploaded!")
        return data


