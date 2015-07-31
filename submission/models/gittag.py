from django.db import models
from django import forms
from django.http import HttpResponse
from django.utils.html import escape

from .base import SubmissionComponent, SubmittedComponent
from submission.forms import ComponentForm as BaseComponentForm, SubmissionForm as BaseSubmissionForm

import os, pipes

class GitTagComponent(SubmissionComponent):
    check = models.BooleanField(default=False, help_text="Check that the repository and tag really exists? Implies that all submitted repos must be public http:// or https:// URLs.")
    # ^ currently unimplemented. See comment at bottom of this file.
    prefix = models.CharField(blank=True, null=True, max_length=200, help_text='Prefix that the URL *must* start with. (e.g. "git@github.com:" or "https://github.com", blank for none.)')
    class Meta:
        app_label = 'submission'

class SubmittedGitTag(SubmittedComponent):
    component = models.ForeignKey(GitTagComponent, null=False)
    url = models.CharField(null=False, blank=False, max_length=500, verbose_name='Repository URL', help_text='Clone URL for your repository, like "https://server/user/repo.git" or "git@server:user/repo.git".')
    tag = models.CharField(blank=False, null=False, max_length=200, verbose_name='Tag name', help_text='The tag you\'re submitting: created like "git tag submitted_code; git push origin --tags"')
    class Meta:
        app_label = 'submission'

    def get_url(self):
        return self.url

    def get_size(self):
        return None

    def get_filename(self):
        return None

    def get_filename_display(self):
        return "clone.sh"

    def _clone_cmd(self, slug=None):
        if slug:
            dirname = slug
        else:
            dirname = 'repo'
        content = []
        content.append(u"# Submitted Git tag can be retrieved with the command below.")
        content.append(u"# repo_url:%s" % (self.url,))
        content.append(u"# tag:%s" % (self.tag,))
        content.append(u"git clone %s %s && cd %s && git checkout tags/%s" % (
            pipes.quote(self.url),
            pipes.quote(dirname), pipes.quote(dirname),
            pipes.quote(self.tag),
        ))
        return '\n'.join(content)

    def download_response(self, slug=None, **kwargs):
        response = HttpResponse(content_type="text/plain;charset=utf-8")
        response.write(self._clone_cmd(slug=slug).encode('utf-8'))
        return response

    def add_to_zip(self, zipfile, prefix=None, slug=None, **kwargs):
        content = self._clone_cmd(slug=slug)
        fn = self.component.slug+".sh"
        if prefix:
            fn = os.path.join(prefix, fn)
        zipfile.writestr(fn, content.encode('utf-8'))

class GitTag:
    label = "gittag"
    name = "Git tag"
    descr = "a tag within a Git repository"
    Component = GitTagComponent
    SubmittedComponent = SubmittedGitTag

    class ComponentForm(BaseComponentForm):
        class Meta:
            model = GitTagComponent
            fields = ['title', 'description', 'prefix', 'deleted']

        def __init__(self, *args, **kwargs):
            super(GitTag.ComponentForm, self).__init__(*args, **kwargs)
            self.fields.__delitem__('specified_filename')
            self.fields['description'].widget = forms.Textarea(attrs={'cols': 50, 'rows': 5})

    class SubmissionForm(BaseSubmissionForm):
        class Meta:
            model = SubmittedGitTag
            fields = ['url', 'tag']
            widgets = {
                'url': forms.TextInput(attrs={'style':'width:25em'}),
            }

        def clean_tag(self):
            # https://www.kernel.org/pub/software/scm/git/docs/git-check-ref-format.html
            tag = self.cleaned_data['tag']

            if '..' in tag:
                raise forms.ValidationError('Tag names cannot contain "..".')

            return tag

        def clean_url(self):
            url = self.cleaned_data['url']
            if self.check_is_empty(url):
                raise forms.ValidationError("No URL given.")

            if self.component.prefix:
                # check that the URL starts with the provided prefix
                if not url.startswith(self.component.prefix):
                    raise forms.ValidationError('Submitted URL must start with "%s".' % (self.component.prefix))

            if self.component.check:
                raise NotImplementedError()
            return url

SubmittedGitTag.Type = GitTag
GitTagComponent.Type = GitTag

# Using gitpython, a check for the tag existing course be done like this, but the .fetch() could be arbitrarily expensive
# import git
# repo = git.Repo.init(tempdir)
# origin = repo.create_remote('origin', REMOTE_URL)
# origin.fetch()
# print [t.name for t in repo.tags]
