from base import *
import submission.forms
from django.forms.widgets import Textarea, TextInput
from django import forms

# model objects must be defined at top-level so Django notices them for DB creation, etc.
class URLComponent(SubmissionComponent):
    class Meta:
        app_label = 'submission'

class SubmittedURL(SubmittedComponent):
    component = models.ForeignKey(URLComponent, null=False)
    url = models.URLField(verify_exists=True,blank = True)
    class Meta:
        app_label = 'submission'
    def get_url(self):
        return self.url
    def get_size(self):
        return None    

# class containing all pieces for this submission type
class URL:
    label = "url"
    name = "URL"
    Component = URLComponent
    SubmittedComponent = SubmittedURL

    class ComponentForm(submission.forms.ComponentForm):
        class Meta:
            model = URLComponent
            fields = ['title', 'description']
            widgets = {
                'description': Textarea(attrs={'cols':50, 'rows':5}),
            }

    class SubmissionForm(submission.forms.SubmissionForm):
        class Meta:
            model = SubmittedURL
            fields = ['url']
            widgets = {
                'url': TextInput(attrs={'style':'width:25em'}),
            }
        def clean_url(self):
            url = self.cleaned_data['url']
            if self.check_is_empty(url):
                raise forms.ValidationError("No URL given.")
            return url;

SubmittedURL.Type = URL
URLComponent.Type = URL
