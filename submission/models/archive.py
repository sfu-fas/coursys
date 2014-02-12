from base import *
import submission.forms
from django.forms.widgets import Textarea, TextInput, FileInput
from django import forms
from django.http import HttpResponse


class ArchiveComponent(SubmissionComponent):
    "An archive file (TGZ/ZIP/RAR) submission component"
    max_size = models.PositiveIntegerField(help_text="Maximum size of the archive file, in kB.", null=False, default=10000)
    allowed_types = {
            "ZIP": [".zip"],
            "RAR": [".rar"],
            "TGZ": [".tar.gz", ".tgz"]
            }
    mime_types = {
            ".zip": "application/zip",
            ".rar": "application/x-rar-compressed",
            ".tgz": "application/x-compressed",
            ".tar.gz": "application/x-compressed"
            }
    class Meta:
        app_label = 'submission'


class SubmittedArchive(SubmittedComponent):
    component = models.ForeignKey(ArchiveComponent, null=False)
    archive = models.FileField(upload_to=submission_upload_path, blank=False, max_length=500,
                               storage=SubmissionSystemStorage, verbose_name='Archive submission')
        
    class Meta:
        app_label = 'submission'
    def get_url(self):
        return self.archive.url
    def get_size(self):
        try:
            return self.archive.size
        except OSError:
            return None
    def get_filename(self):
        return os.path.split(self.archive.name)[1]

    def download_response(self):
        # figure out the MIME type
        for ext in self.component.mime_types:
            if self.archive.name.lower().endswith(ext):
                content_type = self.component.mime_types[ext]
                break

        response = HttpResponse(content_type=content_type)
        self.sendfile(self.archive, response)
        return response

    def add_to_zip(self, zipfile, prefix=None):
        filename = self.file_filename(self.archive, prefix)
        zipfile.write(self.archive.path, filename)

class Archive:
    label = "archive"
    name = "Archive"
    descr = "an archive file (TGZ/ZIP/RAR)"
    Component = ArchiveComponent
    SubmittedComponent = SubmittedArchive
    
    class ComponentForm(submission.forms.ComponentForm):
        class Meta:
            model = ArchiveComponent
            fields = ['title', 'description', 'max_size', 'specified_filename', 'deleted']
        def __init__(self, *args, **kwargs):
            super(Archive.ComponentForm, self).__init__(*args, **kwargs)
            self.fields['description'].widget = Textarea(attrs={'cols': 50, 'rows': 5})

    class SubmissionForm(submission.forms.SubmissionForm):
        class Meta:
            model = SubmittedArchive
            fields = ['archive']
            widgets = {'archive': FileInput()}
        def clean_archive(self):
            data = self.cleaned_data['archive']
            return self.check_uploaded_data(data)

SubmittedArchive.Type = Archive
ArchiveComponent.Type = Archive
