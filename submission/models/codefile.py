from base import *
import submission.forms
from django.forms.widgets import Textarea, TextInput, FileInput, SelectMultiple
from django import forms
from django.http import HttpResponse
from os.path import splitext
from django.conf import settings
MEDIA_URL = settings.MEDIA_URL
from django.template import Context, Template
import re

FILENAME_TYPES = [ # type of filename checking: checked by Codefile.SubmissionForm.clean_code
        ('INS', 'Filename must match, but uppercase and lowercase don\'t matter'),
        ('MAT', 'Filename must match exactly'),
        ('EXT', 'File Extension: the filename must end as specified'),
        ('REX', 'Regular Expression: the "filename" above must be a regular expression to match'),
        ]

class CodefileComponent(SubmissionComponent):
    "A Source Code submission component"
    max_size = models.PositiveIntegerField(help_text="Maximum size of the file, in kB.", null=False, default=200)
    filename = models.CharField(max_length=500, null=False, help_text='Required filename for submitted files. Interpreted as specified in the filename type')
    filename_type = models.CharField(choices=FILENAME_TYPES, max_length=3, blank=False, null=False, default='INS', help_text='How should your filename be interpreted?')

    class Meta:
        app_label = 'submission'

    @classmethod
    def build_from_codecomponent(cls, codecomp):
        """
        Build a CodefileComponent from a CodeComponent, for upgrading during semester migration.
        """
        newcomp = cls()
        # copy fields that are the same
        newcomp.activity = codecomp.activity
        newcomp.title = codecomp.title
        newcomp.description = codecomp.description
        newcomp.position = codecomp.position
        newcomp.slug = codecomp.slug
        newcomp.deleted = codecomp.deleted
        newcomp.max_size = codecomp.max_size

        # handle filename restrictions
        newcomp.specified_filename = ''
        extensions = codecomp.allowed.split(',')
        if codecomp.specified_filename:
            newcomp.filename = codecomp.specified_filename
            newcomp.filename_type = 'MAT'
        elif len(extensions) == 0:
            # shouldn't happen
            newcomp.filename = '^.*$'
            newcomp.filename_type = 'REX'
        elif len(extensions) == 1:
            ext = extensions[0]
            newcomp.filename = ext
            newcomp.filename_type = 'EXT'
        else:
            extensions_re = [re.escape(e) for e in extensions]
            newcomp.filename = '^.*(' + '|'.join(extensions_re) + ')$'
            newcomp.filename_type = 'REX'

        return newcomp


class SubmittedCodefile(SubmittedComponent):
    component = models.ForeignKey(CodefileComponent, null=False)
    code = models.FileField(upload_to=submission_upload_path, blank=False, max_length=500, storage=SubmissionSystemStorage,
                            verbose_name='Code submission')

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
    name = "Code file"
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
            del self.fields['specified_filename'] # our filename and filename.type do a better job

        def clean_filename_type(self):
            filename_type = self.data['filename_type']
            filename = self.data['filename']
            if filename_type == 'REX':
                try:
                    re.compile(filename)
                except re.error as e:
                    msg = unicode(e)
                    raise forms.ValidationError(u'Given filename is not a valid regular expression. Error: "%s".' % (msg))
            return filename_type
     

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

            if not self.component.filename:
                # no filename to check, so pass.
                pass

            elif self.component.filename_type == 'INS':
                if self.component.filename.lower() != data.name.lower():
                    raise forms.ValidationError(u'File name must be "%s".' % (self.component.filename))

            elif self.component.filename_type == 'MAT':
                if self.component.filename != data.name:
                    raise forms.ValidationError(u'File name must be "%s".' % (self.component.filename))

            elif self.component.filename_type == 'EXT':
                if not data.name.endswith(self.component.filename):
                    raise forms.ValidationError(u'File name must have extension "%s".' % (self.component.filename))

            elif self.component.filename_type == 'REX':
                regex = re.compile(self.component.filename)
                if not regex.match(data.name):
                    raise forms.ValidationError(u'The filename is not in the correct format. It must match the regular expression "%s".' % (self.component.filename))

            else:
                raise ValueError, "Unexpected filename_type for submission component."

            return data

SubmittedCodefile.Type = Codefile
CodefileComponent.Type = Codefile
