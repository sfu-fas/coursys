from base import *
import submission.forms
from django.forms.widgets import Textarea, TextInput, FileInput
from django import forms
from django.http import HttpResponse


class WordComponent(SubmissionComponent):
    "A Word/OpenDoc file submission component"
    max_size = models.PositiveIntegerField(help_text="Maximum size of the Word/OpenDoc file, in kB.", null=False, default=10000)
    allowed_types = {
            "WORD": [".doc", '.docx'],
            "OPENDOC": [".odt"]
            }
    mime_types = {
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".odt": "application/vnd.oasis.opendocument.text", 
            }
    class Meta:
        app_label = 'submission'
    def visible_type(self):
        "Soft-delete this type to prevent creation of new"
        return False


class SubmittedWord(SubmittedComponent):
    component = models.ForeignKey(WordComponent, null=False)
    word = models.FileField(upload_to=submission_upload_path, blank=False, max_length=500, storage=SubmissionSystemStorage,
                            verbose_name='Word document submission')
        
    class Meta:
        app_label = 'submission'
    def get_url(self):
        return self.word.url
    def get_size(self):
        try:
            return self.word.size
        except OSError:
            return None
    def get_filename(self):
        return os.path.split(self.word.name)[1]

    def download_response(self):
        # figure out the MIME type
        for ext in self.component.mime_types:
            if self.word.name.lower().endswith(ext):
                content_type = self.component.mime_types[ext]
                break

        response = HttpResponse(content_type=content_type)
        self.sendfile(self.word, response)
        return response

    def add_to_zip(self, zipfile, prefix=None):
        filename = self.file_filename(self.word, prefix)
        zipfile.write(self.word.path, filename)

class Word:
    label = "word"
    name = "Word"
    descr = "a MS Word or OpenDocument file"
    Component = WordComponent
    SubmittedComponent = SubmittedWord
    
    class ComponentForm(submission.forms.ComponentForm):
        class Meta:
            model = WordComponent
            fields = ['title', 'description', 'max_size', 'specified_filename', 'deleted']
        def __init__(self, *args, **kwargs):
            super(Word.ComponentForm, self).__init__(*args, **kwargs)
            self.fields['description'].widget = Textarea(attrs={'cols': 50, 'rows': 5})
            self.fields['max_size'].label=mark_safe("Max size")

    class SubmissionForm(submission.forms.SubmissionForm):
        class Meta:
            model = SubmittedWord
            fields = ['word']
            widgets = {'word': FileInput()}
        def clean_word(self):
            data = self.cleaned_data['word']
            return self.check_uploaded_data(data)

SubmittedWord.Type = Word
WordComponent.Type = Word
