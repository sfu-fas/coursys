# TODO: write better help_text (incl allow_math=False case)
# TODO: ta module uses creole for offer_text  ** FIXED, although it calls markup_to_html directly, which isn't great **
# TODO: discipline module uses textile
# TODO: ta TAContactForm uses textile
# TODO: just a "text with line breaks" markup
# TODO: ... and then use for grade/marking comments?
# TODO: the markup choice dropdown is going to be confusing for some people: simplify or something?

from django.db import models
from django.utils.safestring import mark_safe, SafeText
from django.utils.html import linebreaks
from django.conf import settings
from cache_utils.decorators import cached

from grades.models import Activity

import re, os, subprocess
import pytz
import creoleparser
import bleach
from textile import textile_restricted


MARKUP_CHOICES = [
    ('plain', 'Plain Text'),
    ('creole', 'WikiCreole'),
    ('markdown', 'Markdown'),
    ('textile', 'Textile'),
    ('html', 'HTML'),
]
MARKUP_CHOICES_WYSIWYG = MARKUP_CHOICES + [('html-wysiwyg', 'HTML editor')]
MARKUPS = dict(MARKUP_CHOICES)
# must be in-sync with object in markup-edit.js

allowed_tags_restricted = bleach.sanitizer.ALLOWED_TAGS + [ # allowed in discussion, etc
    'h3', 'h4', 'pre', 'p', 'dl', 'dt', 'dd',
    'dfn', 'q', 'del', 'ins', 's', 'sub', 'sup', 'u',
]
allowed_tags = allowed_tags_restricted + [ # allowed on pages and advisor notes
    'h2', 'img', 'div',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
]
allowed_attributes = bleach.sanitizer.ALLOWED_ATTRIBUTES
allowed_attributes['pre'] = ['lang']


def sanitize_html(html, restricted=False):
    """
    Sanitize HTML we got from the user so it's safe to include in the page
    """
    # TODO: document the HTML subset allowed (particularly <pre lang="python">)
    allowed = allowed_tags_restricted if restricted else allowed_tags
    return mark_safe(bleach.clean(html, tags=allowed, attributes=allowed_attributes, strip=True))


def ensure_sanitary_markup(markup, markuplang, restricted=False):
    """
    Double-check that the markup we're about to store is safe.

    :param markup: markup
    :param markuplang: markup language contained in markup argument
    :param restricted: use the restricted HTML subset?
    :return: sanitary markup
    """
    if markuplang == 'html' and not isinstance(markup, SafeText):
        # HTML input, but not a SafeText (which comes from sanitize_html)
        return sanitize_html(markup, restricted=restricted)

    # otherwise, we trust the markup language processor to safe output.
    return markup


def markdown_to_html(markup):
    sub = subprocess.Popen([os.path.join(settings.BASE_DIR, 'courselib', 'markdown2html.rb')], stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE)
    stdoutdata, stderrdata = sub.communicate(input=markup.encode('utf8'))
    ret = sub.wait()
    if ret != 0:
        raise RuntimeError('markdown2html.rb did not return successfully')
    return stdoutdata.decode('utf8')


@cached(36000)
def markup_to_html(markup, markuplang, offering=None, pageversion=None, html_already_safe=False, restricted=False):
    """
    Master function to convert one of our markup languages to HTML (safely).

    :param markup: the markup code
    :param markuplang: the markup language, from MARKUP_CHOICES
    :param offering: the course offering we're converting for
    :param pageversion: the PageVersion we're converting for
    :param html_already_safe: markuplang=='html' and markup has already been through sanitize_html()
    :param restricted: use the restricted HTML subset for discussion (preventing format bombs)
    :return: HTML markup
    """
    assert isinstance(markup, str)
    if markuplang == 'creole':
        if offering:
            Creole = ParserFor(offering, pageversion)
        elif pageversion:
            Creole = ParserFor(pageversion.page.offering, pageversion)
        else:
            Creole = ParserFor(offering, pageversion)
        # Creole.text2html returns utf-8 bytes: standardize all output to unicode
        html = Creole.text2html(markup).decode('utf8')
        if restricted:
            html = sanitize_html(html, restricted=True)

    elif markuplang == 'markdown':
        # TODO: the due_date etc tricks that are available in wikicreole
        html = markdown_to_html(markup)
        if restricted:
            html = sanitize_html(html, restricted=True)

    elif markuplang == 'textile':
        html = textile_restricted(markup, lite=False)
        if restricted:
            html = sanitize_html(html, restricted=True)

    elif markuplang == 'html' or markuplang == 'html-wysiwyg':
        # TODO: the due_date etc tricks that are available in wikicreole
        if html_already_safe:
            # caller promises sanitize_html() has already been called on the input
            html = markup
        else:
            html = sanitize_html(markup, restricted=restricted)

    elif markuplang == 'plain':
        html = mark_safe(linebreaks(markup, autoescape=True))

    else:
        raise NotImplementedError()

    assert isinstance(html, str)
    return mark_safe(html.strip())




# custom form field

from django import forms


class MarkupContentWidget(forms.MultiWidget):
    template_name = 'markup-content-widget.html'
    def __init__(self):
        widgets = (
            forms.Textarea(attrs={'cols': 70, 'rows': 20}),
            forms.Select(),
            forms.CheckboxInput(),
        )
        super(MarkupContentWidget, self).__init__(widgets)

    def get_context(self, *args, **kwargs):
        context = super().get_context(*args, **kwargs)
        context['allow_math'] = self.allow_math
        return context

    def decompress(self, value):
        if value is None:
            return ['', self.default_markup, False]
        return value


class MarkupContentField(forms.MultiValueField):
    widget = MarkupContentWidget

    def __init__(self, with_wysiwyg=False, rows=20, default_markup='creole', allow_math=True, restricted=False,
                 max_length=100000, *args, **kwargs):
        choices = MARKUP_CHOICES_WYSIWYG if with_wysiwyg else MARKUP_CHOICES
        fields = [
            forms.CharField(required=True, max_length=max_length),
            forms.ChoiceField(choices=choices, required=True),
            forms.BooleanField(required=False),
        ]

        help_url = '/docs/markup' # hard-coded URL because lazy-evaluating them is hard
        default_help = '<a href="' + help_url + '">Markup language</a> used in the content'
        if allow_math:
            default_help += ', and should <a href="http://www.mathjax.org/">MathJax</a> be used for displaying TeX formulas?'
        default_help += ' <span id="markup-help"></span>'
        help_text = kwargs.pop('help_text', mark_safe(default_help))

        super(MarkupContentField, self).__init__(fields, required=False,
            help_text=help_text,
            *args, **kwargs)

        self.fields[0].required = True
        self.widget.widgets[0].attrs['rows'] = rows
        self.fields[1].required = True
        self.widget.widgets[1].choices = choices

        self.widget.allow_math = allow_math
        self.restricted = restricted
        self.widget.default_markup = default_markup

    def compress(self, data_list):
        return data_list

    def clean(self, value):
        content, markup, math = super(MarkupContentField, self).clean(value)

        if markup == 'html-wysiwyg':
            # the editor is a UI nicety only
            markup = 'html'

        if markup == 'html':
            content = sanitize_html(content, restricted=self.restricted)

        math = math and self.widget.allow_math

        return content, markup, math


def MarkupContentMixin(field_name='content'):
    """
    Mixin for a model that uses MarkupContentField. Usage should be something like:
        class MessageForm(MarkupContentMixin(field_name='content'), forms.ModelForm):
            content = MarkupContentField()

    Assumes model objects with content in o.field_name and o.config['markup'] and o.config['math'] to specify the
    markup language and math status.
    """
    class _MarkupContentMixin(object):
        def __init__(self, instance=None, *args, **kwargs):
            super(_MarkupContentMixin, self).__init__(instance=instance, *args, **kwargs)
            self.field_name = field_name
            if instance:
                try:
                    self.initial[self.field_name] = [getattr(instance, self.field_name), instance.markup(), instance.math()]
                except TypeError:
                    self.initial[self.field_name] = [getattr(instance, self.field_name), instance.markup, instance.math]
            else:
                self.initial[self.field_name] = ['', self[self.field_name].field.widget.default_markup, False]

        def clean(self):
            content, markup, math = self.cleaned_data.get(self.field_name, ['', '', False])
            if markup not in MARKUPS:
                raise forms.ValidationError('Invalid markup choice')
            self.cleaned_data[self.field_name] = content
            self.cleaned_data['_markup'] = markup
            self.cleaned_data['_math'] = math
            return self.cleaned_data

        def save(self, commit=True, *args, **kwargs):
            instance = super(_MarkupContentMixin, self).save(commit=False, *args, **kwargs)
            setattr(instance, self.field_name, self.cleaned_data[self.field_name])
            try:
                instance.set_markup(self.cleaned_data['_markup'])
                instance.set_math(self.cleaned_data['_math'])
            except AttributeError:
                instance.markup = self.cleaned_data['_markup']
                instance.math = self.cleaned_data['_math']

            if commit:
                instance.save()
            return instance

    return _MarkupContentMixin


# custom creoleparser Parser class

from genshi.core import Markup

brushre = r"[\w\-#]+"


class AbbrAcronym(creoleparser.elements.InlineElement):
    # handles a subset of the abbreviation/acronym extension
    # http://www.wikicreole.org/wiki/AbbreviationAndAcronyms
    def __init__(self):
        super(AbbrAcronym, self).__init__('abbr', ['^', '^'])

    def _build(self, mo, element_store, environ):
        try:
            abbr, title = mo.group(1).split(":", 1)
        except ValueError:
            abbr = mo.group(1)
            title = None
        return creoleparser.core.bldr.tag.__getattr__('abbr')(
            creoleparser.core.fragmentize(abbr,
                                          self.child_elements,
                                          element_store, environ), title=title)


class HTMLEntity(creoleparser.elements.InlineElement):
    # Allows HTML elements to be passed through
    def __init__(self):
        super(HTMLEntity, self).__init__('span', ['&', ';'])
        self.regexp = re.compile(self.re_string())

    def re_string(self):
        return '&([A-Za-z]\w{1,24}|#\d{2,7}|#[Xx][0-9a-zA-Z]{2,6});'

    def _build(self, mo, element_store, environ):
        content = mo.group(1)
        return creoleparser.core.bldr.tag.__getattr__('span')(Markup('&' + content + ';'))


class CodeBlock(creoleparser.elements.BlockElement):
    """
    A block of code that gets syntax-highlited
    """

    def __init__(self):
        super(CodeBlock, self).__init__('pre', ['{{{', '}}}'])
        self.regexp = re.compile(self.re_string(), re.DOTALL + re.MULTILINE)
        self.regexp2 = re.compile(self.re_string2(), re.MULTILINE)

    def re_string(self):
        start = '^\{\{\{\s*\[(' + brushre + ')\]\s*\n'
        content = r'(.+?\n)'
        end = r'\}\}\}\s*?$'
        return start + content + end

    def re_string2(self):
        """Finds a closing token with a space at the start of the line."""
        return r'^ (\s*?\}\]\s*?\n)'

    def _build(self, mo, element_store, environ):
        lang = mo.group(1)
        code = mo.group(2).rstrip()

        return creoleparser.core.bldr.tag.__getattr__(self.tag)(
            creoleparser.core.fragmentize(code, self.child_elements,
                                          element_store, environ, remove_escapes=False),
            class_="highlight lang-" + lang,
            lang=lang # the most restrictive markup rendering strips the class attribute, but not lang.
        )


def _find_activity(offering, arg_string):
    """
    Find activity from the arg_string from a macro. Return error message string if it can't be found.
    """
    act_name = arg_string.strip()
    attrs = {}
    acts = Activity.objects.filter(offering=offering, deleted=False).filter(
        models.Q(name=act_name) | models.Q(short_name=act_name))
    if len(acts) == 0:
        return '[No activity "%s"]' % (act_name)
    elif len(acts) > 1:
        return '[There is both a name and short name "%s"]' % (act_name)
    else:
        return acts[0]
        due = act.due_date


local_tz = pytz.timezone(settings.TIME_ZONE)


def _duedate(offering, dateformat, macro, environ, *act_name):
    """
    creoleparser macro for due datetimes

    Must be created in a closure by ParserFor with offering set (since that
    doesn't come from the parser).
    """
    act = _find_activity(offering, macro['arg_string'])
    attrs = {}
    if isinstance(act, Activity):
        due = act.due_date
        if due:
            iso8601 = local_tz.localize(due).isoformat()
            text = act.due_date.strftime(dateformat)
            attrs['title'] = iso8601
        else:
            text = '["%s" has no due date specified]' % (act.name)
            attrs['class'] = 'empty'
    else:
        # error
        text = act
        attrs['class'] = 'empty'

    return creoleparser.core.bldr.tag.__getattr__('span')(text, **attrs)


def _activitylink(offering, macro, environ, *act_name):
    act = _find_activity(offering, macro['arg_string'])
    attrs = {}
    if isinstance(act, Activity):
        text = act.name
        attrs['href'] = act.get_absolute_url()
    else:
        # error
        text = act
        attrs['class'] = 'empty'

    return creoleparser.core.bldr.tag.__getattr__('a')(text, **attrs)


def _pagelist(offering, pageversion, macro, environ, prefix=None):
    # all pages [with the given prefix] for this offering
    from pages.models import Page
    if prefix:
        pages = Page.objects.filter(offering=offering, label__startswith=prefix)
    else:
        pages = Page.objects.filter(offering=offering)

    # ... except this page (if known)
    if pageversion:
        pages = pages.exclude(id=pageversion.page_id)

    elements = []
    for p in pages:
        link = creoleparser.core.bldr.tag.__getattr__('a')(p.current_version().title or p.label, href=p.label)
        li = creoleparser.core.bldr.tag.__getattr__('li')(link)
        elements.append(li)
    return creoleparser.core.bldr.tag.__getattr__('ul')(elements, **{'class': 'filelist'})


class ParserFor(object):
    """
    Class to hold the creoleparser objects for a particular CourseOffering.

    (Needs to be specific to the offering so we can select the right activities/pages in macros.)
    """

    def __init__(self, offering, pageversion=None):
        self.offering = offering
        self.pageversion = pageversion

        def duedate_macro(macro, environ, *act_name):
            return _duedate(self.offering, '%A %B %d %Y', macro, environ, *act_name)

        def duedatetime_macro(macro, environ, *act_name):
            return _duedate(self.offering, '%A %B %d %Y, %H:%M', macro, environ, *act_name)

        def activitylink_macro(macro, environ, *act_name):
            return _activitylink(self.offering, macro, environ, *act_name)

        def pagelist_macro(macro, environ, prefix=None):
            return _pagelist(self.offering, self.pageversion, macro, environ, prefix)

        if self.offering:
            nb_macros = {
                'duedate': duedate_macro,
                'duedatetime': duedatetime_macro,
                'pagelist': pagelist_macro,
                'activitylink': activitylink_macro,
            }
        else:
            nb_macros = None
        CreoleBase = creoleparser.creole11_base(non_bodied_macros=nb_macros, add_heading_ids='h-')

        class CreoleDialect(CreoleBase):
            codeblock = CodeBlock()
            abbracronym = AbbrAcronym()
            htmlentity = HTMLEntity()
            strikethrough = creoleparser.elements.InlineElement('del', '--')

            def __init__(self):
                self.custom_elements = [self.abbracronym, self.strikethrough]
                super(CreoleDialect, self).__init__()

            @property
            def inline_elements(self):
                inline = super(CreoleDialect, self).inline_elements
                inline.append(self.abbracronym)
                inline.append(self.strikethrough)
                inline.append(self.htmlentity)
                return inline

            @property
            def block_elements(self):
                blocks = super(CreoleDialect, self).block_elements
                blocks.insert(0, self.codeblock)
                return blocks

        self.parser = creoleparser.core.Parser(CreoleDialect)
        self.text2html = self.parser.render
