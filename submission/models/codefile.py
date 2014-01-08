from base import *
import submission.forms
from django.forms.widgets import Textarea, TextInput, FileInput, SelectMultiple
from django import forms
from django.http import HttpResponse
from os.path import splitext
from django.conf import settings
MEDIA_URL = settings.MEDIA_URL
from django.template import Context, Template

FILENAME_TYPES = [
        ('INS', 'Case-Insensitive Exact Match'),
        ('MAT', 'Exact Match'),
        ('EXT', 'File Extension'),
        ('REX', 'Regular Expression'),
        ]

class CodefileComponent(SubmissionComponent):
    "A Source Code submission component"
    max_size = models.PositiveIntegerField(help_text="Maximum size of the file, in kB.", null=False, default=200)
    filename = models.CharField(max_length=500, null=False, help_text='Required filename for submitted files. Interpreted according as specified in the filename type')
    filename_type = models.CharField(choices=FILENAME_TYPES, max_length=3, blank=False, null=False, default='INS', help_text='How should your filename be interpreted?')

    class Meta:
        app_label = 'submission'

class SubmittedCodefile(SubmittedComponent):
    component = models.ForeignKey(CodefileComponent, null=False)
    code = models.FileField(upload_to=submission_upload_path, blank=False, max_length=500, storage=SubmissionSystemStorage)

    class Meta:
        app_label = 'submission'
    def get_url(self):
        return self.code.url
    def get_size(self):
        try:
            return self.code.size
        except OSError:
            return None
    def get_filename(self):
        return os.path.split(self.code.name)[1]

    def download_response(self):
        response = HttpResponse(content_type="text/plain")
        self.sendfile(self.code, response)
        return response
    def add_to_zip(self, zipfile, prefix=None):
        filename = self.file_filename(self.code, prefix)
        zipfile.write(self.code.path, filename)

FIELD_TEMPLATE = Template('''<li>
                    {{ field.label_tag }}
                    <div class="inputfield">
                        {{ field }}
			{% if field.errors %}<div class="errortext"><img src="'''+ MEDIA_URL+'''icons/error.png" alt="error"/>&nbsp;{{field.errors.0}}</div>{% endif %}
			<div class="helptext">{{field.help_text}}</div>
                    </div>
                </li>''')
                        
class Codefile:
    label = "codefile"
    name = "Code"
    descr = "a source code file"
    Component = CodefileComponent
    SubmittedComponent = SubmittedCodefile

    class ComponentForm(submission.forms.ComponentForm):
        class Meta:
            model = CodefileComponent
            fields = ['title', 'description', 'max_size', 'filename', 'filename_type', 'deleted']
        
        def __init__(self, *args, **kwargs):
            super(Codefile.ComponentForm, self).__init__(*args, **kwargs)
            self.fields['description'].widget = Textarea(attrs={'cols': 50, 'rows': 5})
            self.fields['max_size'].widget = TextInput(attrs={'style':'width:5em'})
            self.fields['max_size'].label=mark_safe("Max size"+submission.forms._required_star)
            del self.fields['specified_filename'] # our filename and filename.type do a better job

     

    class SubmissionForm(submission.forms.SubmissionForm):
        class Meta:
            model = SubmittedCodefile
            fields = ['code']
            widgets = {'code': FileInput()}
        def clean_code(self):
            data = self.cleaned_data['code']
            if self.check_is_empty(data):
                raise forms.ValidationError("No file submitted.")
            if not self.check_size(data):
                raise forms.ValidationError("File size exceeded max size, component can not be uploaded.")

            raise forms.ValidationError("File name not checked.")

            return data

SubmittedCodefile.Type = Codefile
CodefileComponent.Type = Codefile
