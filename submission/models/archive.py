from base import *
import submission.forms
from django.forms.widgets import Textarea, TextInput, FileInput

class ArchiveComponent(SubmissionComponent):
    "An archive file (TGZ/ZIP/RAR) submission component"
    max_size = models.PositiveIntegerField(help_text="Maximum size of the archive file, in KB.", null=True, default=10000)
    extension = [".zip", ".rar", ".gzip", ".tar"]
    class Meta:
        app_label = 'submission'

class SubmittedArchive(SubmittedComponent):
    component = models.ForeignKey(ArchiveComponent, null=False)
    archive = models.FileField(upload_to="submittedarchive", blank = True) # TODO: change to a more secure directory
    class Meta:
        app_label = 'submission'
    def get_url(self):
        return self.archive.url
    def get_size(self):
        return self.archive.size

class Archive:
    label = "archive"
    name = "Archive"
    Component = ArchiveComponent
    SubmittedComponent = SubmittedArchive
    
    class ComponentForm(submission.forms.ComponentForm):
        class Meta:
            model = ArchiveComponent
            fields = ['title', 'description', 'max_size']
            widgets = {
                'description': Textarea(attrs={'cols': 50, 'rows': 5}),
                'max_size': TextInput(attrs={'style':'width:5em'}),
            }

    class SubmissionForm(submission.forms.SubmissionForm):
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
                raise forms.ValidationError("No file submitted.")
            if not self.check_type(data):
                raise forms.ValidationError('File type incorrect.')
            if not self.check_size(data):
                raise forms.ValidationError("File size exceeded max size, component can not be uploaded.")
            return data

SubmittedArchive.Type = Archive
ArchiveComponent.Type = Archive
