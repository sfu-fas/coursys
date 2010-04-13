from base import *
import submission.forms
from django.forms.widgets import Textarea, TextInput
from django import forms
from django.http import HttpResponse
from django.utils.html import escape


# model objects must be defined at top-level so Django notices them for DB creation, etc.
class URLComponent(SubmissionComponent):
    class Meta:
        app_label = 'submission'

class SubmittedURL(SubmittedComponent):
    component = models.ForeignKey(URLComponent, null=False)
    url = models.URLField(verify_exists=True, null=False, blank=False) # TODO: make missing URL warning only (in case of authentication, etc)
    class Meta:
        app_label = 'submission'
    def get_url(self):
        return self.url
    def get_size(self):
        return None
    
    def download_response(self):
        response = HttpResponse(mimetype="text/html")
        response.write("""<title>%s</title><a href="%s">%s</a>""" % (escape(self.component.title), escape(self.url), escape(self.url)))
        return response

    def add_to_zip(self, zipfile):
        content = '<html><head><META HTTP-EQUIV="Refresh" CONTENT="0; URL='
        if str(self.url).find("://") == -1:
            content += "http://"
        content += self.url
        content += '"></head><body>' \
            + 'If redirecting doesn\' work, click the link <a href="' \
            + escape(self.url) + '">' + escape(self.url) + '</a>' \
            + '</body></html> '
        zipfile.writestr(self.component.slug+".html", content)

# class containing all pieces for this submission type
class URL:
    label = "url"
    name = "URL"
    Component = URLComponent
    SubmittedComponent = SubmittedURL

    class ComponentForm(submission.forms.ComponentForm):
        class Meta:
            model = URLComponent
            fields = ['title', 'description', 'deleted']
            # widgets = {
            #     'description': Textarea(attrs={'cols':50, 'rows':5}),
            # }
        def __init__(self, *args, **kwargs):
            super(URL.ComponentForm, self).__init__(*args, **kwargs)
            self.fields['description'].widget = Textarea(attrs={'cols': 50, 'rows': 5})
            self.fields['deleted'].label=mark_safe("Invisible")

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
