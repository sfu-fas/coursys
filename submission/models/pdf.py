from base import *
import submission.forms
from django.forms.widgets import Textarea, TextInput, FileInput
from django import forms
from django.http import HttpResponse


class PDFComponent(SubmissionComponent):
    "A Acrobat (PDF) submission component"
    max_size = models.PositiveIntegerField(help_text="Maximum size of the PDF file, in kB.", null=False, default=5000)
    allowed_types = {
            "PDF": [".pdf"]
            }
    class Meta:
        app_label = 'submission'


class SubmittedPDF(SubmittedComponent):
    component = models.ForeignKey(PDFComponent, null=False)
    pdf = models.FileField(upload_to=submission_upload_path, blank=False,  max_length=500, 
          storage=SubmissionSystemStorage, verbose_name='PDF submission')
        
    class Meta:
        app_label = 'submission'
    def get_url(self):
        return self.pdf.url
    def get_size(self):
        try:
            return self.pdf.size
        except OSError:
            return None
    def get_filename(self):
        return os.path.split(self.pdf.name)[1]

    def download_response(self):
        response = HttpResponse(content_type="application/pdf")
        self.sendfile(self.pdf, response)
        return response
    def add_to_zip(self, zipfile, prefix=None):
        filename = self.file_filename(self.pdf, prefix)
        zipfile.write(self.pdf.path, filename)

class PDF:
    label = "pdf"
    name = "PDF"
    descr = "an Acrobat document"
    Component = PDFComponent
    SubmittedComponent = SubmittedPDF
    
    class ComponentForm(submission.forms.ComponentForm):
        class Meta:
            model = PDFComponent
            fields = ['title', 'description', 'max_size', 'specified_filename', 'deleted']
            # widgets = {
            #     'description': Textarea(attrs={'cols': 50, 'rows': 5}),
            #     'max_size': TextInput(attrs={'style':'width:5em'}),
            # }
        def __init__(self, *args, **kwargs):
            super(PDF.ComponentForm, self).__init__(*args, **kwargs)
            self.fields['description'].widget = Textarea(attrs={'cols': 50, 'rows': 5})

    class SubmissionForm(submission.forms.SubmissionForm):
        class Meta:
            model = SubmittedPDF
            fields = ['pdf']
            widgets = {'pdf': FileInput()}
        def clean_pdf(self):
            data = self.cleaned_data['pdf']
            return self.check_uploaded_data(data)

SubmittedPDF.Type = PDF
PDFComponent.Type = PDF
