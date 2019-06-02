from django.db import models
from django.http import HttpResponse
from django.forms.widgets import Textarea
from django import forms
from django.utils.safestring import mark_safe

from .base import SubmissionComponent, SubmittedComponent, FileSizeField
from submission.forms import ComponentForm as BaseComponentForm, SubmissionForm as BaseSubmissionForm
from courselib.codemirror_language_list import CODEMIRROR_MODES

import os, re

MAX_TEXT_KB = 100
MAX_TEXT_LENGTH = MAX_TEXT_KB * 1024

LANGUAGE_CHOICES = [(mode, label) for mode, label, _, _ in CODEMIRROR_MODES]
LANGUAGE_CHOICES = sorted(LANGUAGE_CHOICES, key=lambda c: c[1].lower())

FILE_EXT_RE = re.compile('^[A-Za-z0-9]+$')


class LiveCodeComponent(SubmissionComponent):
    is_live_code = True # so we can detect this class to activate codemirror
    language = models.CharField(max_length=50, null=False, verbose_name='Programming Language', choices=LANGUAGE_CHOICES,
                               help_text='Syntax highlighting that will be used in the entry box.')
    file_ext = models.CharField(max_length=10, null=False, verbose_name='File Extension',
                               help_text='File extension you want when downloading the results (like “py” for Python code).')
    max_size = FileSizeField(help_text="Maximum length, in kB.", null=False, default=10)
    class Meta:
        app_label = 'submission'

    def mode_script_element(self):
        url, integrity = [(url, integrity) for mode, label, url, integrity in CODEMIRROR_MODES if mode == self.language][0]
        return mark_safe('<script src="%s" integrity="sha256-%s" crossorigin="anonymous" referrerpolicy="no-referrer"></script>' % (url, integrity))


class SubmittedLiveCode(SubmittedComponent):
    component = models.ForeignKey(LiveCodeComponent, null=False, on_delete=models.PROTECT)
    text = models.TextField(null=False, blank=False, max_length=MAX_TEXT_LENGTH, verbose_name='Code')
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
        fn = self.component.slug + '.' + self.component.file_ext

        if prefix:
            fn = os.path.join(prefix, fn)
        zipfile.writestr(fn, self.text.encode('utf-8'))


class LiveCode:
    label = "livecode"
    name = "Live Code"
    descr = "immediate entry of code in a programming language"
    Component = LiveCodeComponent
    SubmittedComponent = SubmittedLiveCode

    class ComponentForm(BaseComponentForm):
        class Meta:
            model = LiveCodeComponent
            fields = ['title', 'description', 'language', 'file_ext', 'max_size', 'deleted']

        def __init__(self, *args, **kwargs):
            super(LiveCode.ComponentForm, self).__init__(*args, **kwargs)
            self.fields.__delitem__('specified_filename')
            self.fields['description'].widget = Textarea(attrs={'cols': 50, 'rows': 5})

        def clean_file_ext(self):
            ext = self.cleaned_data['file_ext']
            if ext.startswith('.'):
                ext = ext[1:]
            if not FILE_EXT_RE.match(ext):
                raise forms.ValidationError('File extensions can contain only letters and numbers.')
            return ext

        def clean_max_size(self):
            max_size = self.cleaned_data['max_size']
            if max_size > MAX_TEXT_KB:
                raise forms.ValidationError('Cannot be more than %i kB.' % (MAX_TEXT_KB))
            return max_size

    class SubmissionForm(BaseSubmissionForm):
        class Meta:
            model = SubmittedLiveCode
            fields = ['text']
            widgets = {
                'text': Textarea(attrs={'cols': 50, 'rows': 10}),
            }

        def clean_text(self):
            text = self.cleaned_data['text']
            if  len(text.encode('utf-8')) > self.component.max_size * 1024:
                raise forms.ValidationError("Content exceeded max size of %i kB." % (self.component.max_size,))
            return text


SubmittedLiveCode.Type = LiveCode
LiveCodeComponent.Type = LiveCode
