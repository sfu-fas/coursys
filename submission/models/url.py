from django.db import models
from .base import SubmissionComponent, SubmittedComponent
from django.forms.widgets import Textarea, TextInput
from django import forms
from django.http import HttpResponse
from django.utils.html import escape
from submission.forms import ComponentForm as BaseComponentForm, SubmissionForm as BaseSubmissionForm
import os


# model objects must be defined at top-level so Django notices them for DB creation, etc.
class URLComponent(SubmissionComponent):
    check = models.BooleanField(default=False, help_text="Check that the page really exists?  Will reject missing or password-protected URLs.")
    prefix = models.CharField(blank=True, null=True, max_length=200, help_text='Prefix that the URL *must* start with. (e.g. "http://server.com/course/", blank for none.)')
    class Meta:
        app_label = 'submission'

class SubmittedURL(SubmittedComponent):
    component = models.ForeignKey(URLComponent, null=False)
    url = models.URLField(null=False, blank=False, max_length=500, verbose_name="URL submission")
    class Meta:
        app_label = 'submission'
    def get_url(self):
        return self.url
    def get_size(self):
        return None
    def get_filename(self):
        return None
    def get_filename_display(self):
        return "link"
    
    def download_response(self, **kwargs):
        response = HttpResponse(content_type="text/html;charset=utf-8")
        content = """<title>%s</title><a href="%s">%s</a>""" % (escape(self.component.title), escape(self.url), escape(self.url))
        response.write(content.encode('utf-8'))
        return response

    def add_to_zip(self, zipfile, prefix=None, **kwargs):
        content = '<html><head><META HTTP-EQUIV="Refresh" CONTENT="0; URL='
        if str(self.url).find("://") == -1:
            content += "http://"
        content += self.url
        content += '"></head><body>' \
            + 'If redirecting doesn\'t work, click the link <a href="' \
            + escape(self.url) + '">' + escape(self.url) + '</a>' \
            + '</body></html>\n'
        fn = self.component.slug+".html"
        if prefix:
            fn = os.path.join(prefix, fn)
        zipfile.writestr(fn, content)

from submission.models.url_validator import QuickURLValidator
# class containing all pieces for this submission type
class URL:
    label = "url"
    name = "URL"
    descr = "a web page address"
    Component = URLComponent
    SubmittedComponent = SubmittedURL

    class ComponentForm(BaseComponentForm):
        class Meta:
            model = URLComponent
            fields = ['title', 'description', 'check', 'prefix', 'deleted']
            # widgets = {
            #     'description': Textarea(attrs={'cols':50, 'rows':5}),
            # }
        def __init__(self, *args, **kwargs):
            super(URL.ComponentForm, self).__init__(*args, **kwargs)
            self.fields.__delitem__('specified_filename')
            self.fields['description'].widget = Textarea(attrs={'cols': 50, 'rows': 5})

    class SubmissionForm(BaseSubmissionForm):
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

            if self.component.prefix:
                # check that the URL starts with the provided prefix
                if not url.startswith(self.component.prefix):
                    raise forms.ValidationError('Submitted URL must start with "%s".' % (self.component.prefix))

            if self.component.check:
                # instructor asked to check that URLs really exist: do it.
                validator = QuickURLValidator()
                try:
                    validator(url) # throws ValidationError if there's a problem
                except forms.ValidationError:
                    # re-throw to produce a better error message
                    raise forms.ValidationError("The submitted URL doesn't seem to exist: please check the URL and resubmit.")
            return url

SubmittedURL.Type = URL
URLComponent.Type = URL
