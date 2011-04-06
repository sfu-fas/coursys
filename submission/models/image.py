from base import *
import submission.forms
from django.forms.widgets import FileInput, Textarea
from django import forms
from django.http import HttpResponse


class ImageComponent(SubmissionComponent):
    "An image submission component"
    max_size = models.PositiveIntegerField(help_text="Maximum size of the image file, in kB.", null=False, default=1000)
    allowed_types = {
            "PNG": [".png"],
            "GIF": [".gif"],
            "JPEG": [".jpg"],
            }
    mime_types = {
            ".png": "image/png",
            ".gif": "image/gif",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            }
    class Meta:
        app_label = 'submission'


class SubmittedImage(SubmittedComponent):
    component = models.ForeignKey(ImageComponent, null=False)
    image = models.FileField(upload_to=submission_upload_path, blank=False,  max_length=500, 
          storage=SubmissionSystemStorage)
        
    class Meta:
        app_label = 'submission'
    def get_url(self):
        return self.image.url
    def get_size(self):
        try:
            return self.image.size
        except OSError:
            return None
    def get_filename(self):
        return os.path.split(self.image.name)[1]

    def download_response(self):
        # figure out the MIME type
        for ext in self.component.mime_types:
            if self.image.name.lower().endswith(ext):
                mimetype = self.component.mime_types[ext]
                break

        response = HttpResponse(mimetype=mimetype)
        self.sendfile(self.image, response)
        return response
    def add_to_zip(self, zipfile, prefix=None):
        filename = self.file_filename(self.image, prefix)
        zipfile.write(self.image.path, filename)

class Image:
    label = "image"
    name = "Image"
    Component = ImageComponent
    SubmittedComponent = SubmittedImage
    
    class ComponentForm(submission.forms.ComponentForm):
        class Meta:
            model = ImageComponent
            fields = ['title', 'description', 'max_size', 'deleted', 'specified_filename']
        def __init__(self, *args, **kwargs):
            super(Image.ComponentForm, self).__init__(*args, **kwargs)
            self.fields['description'].widget = Textarea(attrs={'cols': 50, 'rows': 5})
            self.fields['max_size'].label=mark_safe("Max size"+submission.forms._required_star)
            self.fields['deleted'].label=mark_safe("Invisible")

    class SubmissionForm(submission.forms.SubmissionForm):
        class Meta:
            model = SubmittedImage
            fields = ['image']
            widgets = {'image': FileInput()}
        def clean_image(self):
            data = self.cleaned_data['image']
            return self.check_uploaded_data(data)

SubmittedImage.Type = Image
ImageComponent.Type = Image
