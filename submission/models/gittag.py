from django.db import models
from django import forms
from django.http import HttpResponse

from django.db.models.fields import TextField
from django.core.validators import URLValidator
from django.utils.encoding import force_text
from django.core.exceptions import ValidationError

from .base import SubmissionComponent, SubmittedComponent
from submission.forms import ComponentForm as BaseComponentForm, SubmissionForm as BaseSubmissionForm

import os, pipes, re

def _tag_allowed(c):
    """
    Is this character allowed in a tag name?
    """
    o = ord(c)
    return o >= 32 and o < 127 and c not in ' ~^:?*[\\'


class GitURLValidator(URLValidator):
    """
    Field for a GIT clone URL that does a reasonable job validating (the two formats in most common use).
    """
    schemes = ['http', 'https']

    ssh_regex = re.compile( # adapted from bits in URLValidator.regex
        r'^(?:\S+@)'  # user authentication
        r'(?:' + URLValidator.ipv4_re + '|' + URLValidator.ipv6_re + '|' + URLValidator.host_re + ')'
        r'(?::)'  # colon
        r'(?:[^\s]*)'  # resource path
        r'\Z', re.IGNORECASE)

    def __call__(self, value):
        value = force_text(value)
        if value.startswith('http://') or value.startswith('https://'):
            # HTTP(S) URLs: superclass can handle it.
            return super(GitURLValidator, self).__call__(value)

        # or try to validate it as a git scp-style URL
        if not self.ssh_regex.match(value):
            raise ValidationError('Enter a valid "http://", "https://", or "user@host:path" URL.')


class GitURLField(TextField):
    default_validators = [GitURLValidator()]
    description = 'Git clone URL'


class GitTagComponent(SubmissionComponent):
    check = models.BooleanField(default=False, help_text="Check that the repository and tag really exists? Implies that all submitted repos must be public http:// or https:// URLs.")
    # ^ currently unimplemented. See comment at bottom of this file.
    prefix = models.CharField(blank=True, null=True, max_length=200, help_text='Prefix that the URL *must* start with. (e.g. "git@github.com:" or "https://github.com", blank for none.)')

    class Meta:
        app_label = 'submission'

class SubmittedGitTag(SubmittedComponent):
    component = models.ForeignKey(GitTagComponent, null=False)
    url = GitURLField(null=False, blank=False, max_length=500, verbose_name='Repository URL', help_text='Clone URL for your repository, like "https://server/user/repo.git" or "git@server:user/repo.git".')
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
        content.append("# Submitted Git tag can be retrieved with the command below.")
        content.append("git clone %s %s && cd %s && git checkout tags/%s" % (
            pipes.quote(self.url),
            pipes.quote(dirname), pipes.quote(dirname),
            pipes.quote(self.tag),
        ))
        content.append("# url:%s" % (self.url,))
        content.append("# tag:%s" % (self.tag,))
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
            widgets = {
                'prefix': forms.TextInput(attrs={'style':'width:30em'}),
            }

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

            if '..' in tag or tag[-1] == '.':
                raise forms.ValidationError('Tag names cannot contain ".." or end with a dot.')

            if not all(_tag_allowed(c) for c in tag):
                raise forms.ValidationError('Tag name contains an illegal character.')

            if tag[0] == '/' or tag[-1] == '/' or '//' in tag:
                raise forms.ValidationError('Tags cannot start or end with a slash, or contain consecutive slashes.')

            if '@{' in tag:
                raise forms.ValidationError('Tags cannot contain "@{".')

            if tag == '@':
                raise forms.ValidationError('"@" is not a valid tag name.')

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
