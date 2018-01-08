from django.db import models
from django.http import HttpResponse
from django.forms.widgets import Textarea, TextInput
from django import forms

from .base import SubmissionComponent, SubmittedComponent, FileSizeField
from submission.forms import ComponentForm as BaseComponentForm, SubmissionForm as BaseSubmissionForm

import os

MAX_TEXT_KB = 100
MAX_TEXT_LENGTH = MAX_TEXT_KB * 1024

class TextComponent(SubmissionComponent):
    max_size = FileSizeField(help_text="Maximum length, in kB.", null=False, default=10)
    class Meta:
        app_label = 'submission'

class SubmittedText(SubmittedComponent):
    component = models.ForeignKey(TextComponent, null=False)
    text = models.TextField(null=False, blank=False, max_length=MAX_TEXT_LENGTH)
    class Meta:
        app_label = 'submission'
    def get_size(self):
        return len(self.text.encode('utf-8'))
    def get_filename(self):
        return None

    def download_response(self, **kwargs):
        response = HttpResponse(content_type="text/plain;charset=utf-8")
        response.write(self.text.encode('utf-8'))
        return response

    def add_to_zip(self, zipfile, prefix=None, **kwargs):
        fn = self.component.slug + ".txt"
        if prefix:
            fn = os.path.join(prefix, fn)
        zipfile.writestr(fn, self.text.encode('utf-8'))

class Text:
    label = "text"
    name = "Text"
    descr = "short text entry"
    Component = TextComponent
    SubmittedComponent = SubmittedText

    class ComponentForm(BaseComponentForm):
        class Meta:
            model = TextComponent
            fields = ['title', 'description', 'max_size', 'deleted']
        def __init__(self, *args, **kwargs):
            super(Text.ComponentForm, self).__init__(*args, **kwargs)
            self.fields.__delitem__('specified_filename')
            self.fields['description'].widget = Textarea(attrs={'cols': 50, 'rows': 5})

        def clean_max_size(self):
            max_size = self.cleaned_data['max_size']
            if max_size > MAX_TEXT_KB:
                raise forms.ValidationError('Cannot be more than %i kB.' % (MAX_TEXT_KB))
            return max_size

    class SubmissionForm(BaseSubmissionForm):
        class Meta:
            model = SubmittedText
            fields = ['text']
            widgets = {
                'text': Textarea(attrs={'cols': 50, 'rows': 10}),
            }
        def clean_text(self):
            text = self.cleaned_data['text']
            if  len(text.encode('utf-8')) > self.component.max_size * 1024:
                raise forms.ValidationError("Content exceeded max size of %i kB." % (self.component.max_size,))
            return text

SubmittedText.Type = Text
TextComponent.Type = Text
