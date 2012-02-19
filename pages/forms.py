from django import forms
from django.db import transaction
from pages.models import Page, PageVersion, READ_ACL_CHOICES, WRITE_ACL_CHOICES

class WikiField(forms.CharField):
    def __init__(self, *args, **kwargs):
        self.widget = forms.Textarea(attrs={'cols': 90, 'rows': 30})
        if 'help_text' not in kwargs:
            kwargs['help_text'] = 'Page formatted in <a href="http://www.wikicreole.org/wiki/AllMarkup">WikiCreole markup</a>.'
        super(WikiField, self).__init__(*args, **kwargs)

class CommentField(forms.CharField):
    def __init__(self, *args, **kwargs):
        self.widget = forms.TextInput(attrs={'size': 60})
        if 'required' not in kwargs:
            kwargs['required'] = False
        if 'help_text' not in kwargs:
            kwargs['help_text'] = 'Comment on this change'
        super(CommentField, self).__init__(*args, **kwargs)



class EditPageFileForm(forms.ModelForm):
    def __init__(self, offering, *args, **kwargs):
        super(EditPageFileForm, self).__init__(*args, **kwargs)
        # force the right course offering into place
        self.offering = offering
        self.fields['offering'].initial = offering.id
        
        # existing data for other fields
        if self.instance.id:
            self.initial['title'] = self.instance.current_version().title
            self.initial['wikitext'] = self.instance.current_version().wikitext
            self.initial['math'] = self.instance.current_version().math()
        
        # tidy up ACL choices: remove NONE
        self.fields['can_read'].choices = [(v,l) for (v,l) in self.fields['can_read'].choices
                                           if v != 'NONE']
        self.fields['can_write'].choices = [(v,l) for (v,l) in self.fields['can_write'].choices
                                           if v != 'NONE']


    def clean_offering(self):
        if self.cleaned_data['offering'] != self.offering:
            raise forms.ValidationError("Wrong course offering.")
        return self.cleaned_data['offering']

    @transaction.commit_on_success
    def clean_label(self):
        label = self.cleaned_data['label']
        error = self.instance.label_okay(label)
        if error:
            raise forms.ValidationError(error)
        return label

    class Meta:
        model = Page
        exclude = ('config')
        widgets = {
            'offering': forms.HiddenInput(),
            'title': forms.TextInput(attrs={'size':50}),
            'label': forms.TextInput(attrs={'size':20}),
        }



class EditPageForm(EditPageFileForm):
    title = forms.CharField(max_length=60, widget=forms.TextInput(attrs={'size':50}))
    wikitext = WikiField()
    comment = CommentField()
    
    math = forms.BooleanField(required=False, help_text='Will this page use <a href="http://www.mathjax.org/">MathJax</a> for displayig TeX or MathML formulas?')

    def save(self, editor, *args, **kwargs):
        # also create the PageVersion object.
        wikitext = self.cleaned_data['wikitext']
        comment = self.cleaned_data['comment']
        title = self.cleaned_data['title']
        pv = PageVersion(title=title, wikitext=wikitext, comment=comment, editor=editor)
        # set config data
        if 'math' in self.cleaned_data:
            pv.set_math(self.cleaned_data['math'])

        self.instance.offering = self.offering
        super(EditPageForm, self).save(*args, **kwargs)
        pv.page=self.instance
        pv.save()


class EditPageFormRestricted(EditPageForm):
    """
    Restricted version of EditPageForm for students.
    """
    def __init__(self, *args, **kwargs):
        super(EditPageFormRestricted, self).__init__(*args, **kwargs)
        del self.fields['title']
        del self.fields['label']
        del self.fields['can_read']
        del self.fields['can_write']
        del self.fields['math']

EditPageForm.restricted_form = EditPageFormRestricted

class EditFileForm(EditPageFileForm):
    file_attachment = forms.FileField(label="File")

    def save(self, editor, *args, **kwargs):
        # also create the PageVersion object.
        upfile = self.cleaned_data['file_attachment']
        pv = PageVersion(file_attachment=upfile, file_mediatype=upfile.content_type,
                         file_name=upfile.name, editor=editor)

        self.instance.offering = self.offering
        super(EditFileForm, self).save(*args, **kwargs)
        pv.page=self.instance
        pv.save()

class EditFileFormRestricted(EditFileForm):
    """
    Restricted version of EditFileForm for students.
    """
    def __init__(self, *args, **kwargs):
        super(EditFileFormRestricted, self).__init__(*args, **kwargs)
        del self.fields['title']
        del self.fields['label']
        del self.fields['can_read']
        del self.fields['can_write']

EditFileForm.restricted_form = EditFileFormRestricted

from importer import HTMLWiki
import urllib2, urlparse

class SiteImportForm(forms.Form):
    url = forms.URLField(required=True, label='URL', widget=forms.TextInput(attrs={'size':70}))
    can_read = forms.ChoiceField(choices=READ_ACL_CHOICES, required=True, initial="ALL")
    can_write = forms.ChoiceField(choices=WRITE_ACL_CHOICES, required=True, initial="STAF")
    
    def __init__(self, offering, editor, *args, **kwargs):
        super(SiteImportForm, self).__init__(*args, **kwargs)
        self.converter = HTMLWiki([])
        self.offering = offering
        self.editor = editor
    
    def _labelize(self, url, title):
        path = urlparse.urlsplit(url).path
        if path:
            parts = path.split('/')
            if len(parts) >= 1 and parts[-1]:
                return parts[-1]
            elif len(parts) >= 2 and parts[-2]:
                return parts[-2]
        
    
    def _import_page(self, url):
        try:
            fh = urllib2.urlopen(url, timeout=20)
            if 'content-type' in fh.headers:
                ctype = fh.headers['content-type'].split(';')[0]
                is_html = ctype in ['text/html', 'application/xhtml+xml']
            else:
                is_html = False
            html = fh.read()
            fh.close()
        except:
            raise forms.ValidationError('Could not fetch "%s".' % (url))
        
        if not is_html:
            raise forms.ValidationError('Not HTML at "%s".' % (url))
        
        try:
            wiki, title, urls = self.converter.from_html_full(html)
        except self.converter.ParseError:
            raise forms.ValidationError("Could not parse the HTML file %s." % (url))
        
        label = self._labelize(url, title)
        if not title:
            title = label
        
        page = Page(offering=self.offering, label=label)
        pv = PageVersion(page=page, editor=self.editor, title=title, wikitext=wiki, comment="imported content")
        #print (page, pv, pv.title)
        #print [urlparse.urljoin(url, u) for u in urls]
        return page, pv, urls
    
    def clean_url(self):
        url = self.cleaned_data['url']
        if not url:
            return None
        
        baseurl = urlparse.urljoin(url, "./")
        needed = set([url])
        done = set()
        found = {}
        errors = []
        while needed:
            if len(found) >= 20:
                break
            url = needed.pop()
            try:
                page, pv, newurls = self._import_page(url)
            except forms.ValidationError as e:
                errors.append(e.messages[0])
            done.add(url)
            newurls = set((urlparse.urljoin(url, u) for u in newurls))
            newurls = set((u for u in newurls if u.startswith(baseurl)))
            needed = needed | newurls - done
            found[page.label] = (page, pv)
            
            #print ">>>", found, errors
            
        return found, errors
    

class PageImportForm(forms.Form):
    file = forms.FileField(required=False)
    url = forms.URLField(required=False, label='URL', widget=forms.TextInput(attrs={'size':70}))
    
    def clean(self):
        url = self.cleaned_data.get('url', None)
        file = self.cleaned_data.get('file', None)
        
        if not url and not file:
            raise forms.ValidationError("Must provide either an HTML file or URL.")
        elif url and file:
            raise forms.ValidationError("Can only provide one of the file and URL.")
        
        return self.cleaned_data

    def _html_to_wiki(self, html):
        converter = HTMLWiki([])
        try:
            wiki = converter.from_html(html)
        except converter.ParseError:
            raise forms.ValidationError("Could not parse the HTML file.")

        return wiki

    
    def clean_url(self):
        url = self.cleaned_data['url']
        if not url:
            return None
        
        try:
            fh = urllib2.urlopen(url, timeout=20)
            html = fh.read()
        except:
            raise forms.ValidationError("Could not fetch the URL.")

        return self._html_to_wiki(html)

    def clean_file(self):
        file = self.cleaned_data['file']
        if file is None:
            return None

        if file.content_type not in ['text/html', 'application/xhtml+xml']:
            raise forms.ValidationError("Only HTML/XHTML files can be imported")

        html = file.read()
        return self._html_to_wiki(html)

