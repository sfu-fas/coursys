from django.core.cache import cache
from django.db import models
from django.utils.safestring import mark_safe
from django.conf import settings

from grades.models import Activity

import re, os, subprocess
import pytz
import creoleparser


MARKUP_CHOICES = [
    ('creole', 'WikiCreole'),
    ('markdown', 'Markdown'),
]


def markdown_to_html(markup):
    sub = subprocess.Popen([os.path.join(settings.BASE_DIR, 'courselib', 'markdown2html.rb')], stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE)
    stdoutdata, stderrdata = sub.communicate(input=markup)
    ret = sub.wait()
    if ret != 0:
        raise RuntimeError('markdown2html.rb did not return successfully')
    return stdoutdata


def markup_to_html(markup, markuplang, offering=None, pageversion=None):
    if markuplang == 'creole':
        if offering:
            Creole = ParserFor(offering, pageversion)
        else:
            Creole = ParserFor(pageversion.page.offering, pageversion)
        html = Creole.text2html(markup)
    elif markuplang == 'markdown':
        # TODO: the due_date etc tricks that are available in wikicreole
        html = markdown_to_html(markup)

    return mark_safe(html.strip())


# custom creoleparser Parser class

import genshi
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
            class_="highlight lang-" + lang)


def _find_activity(offering, arg_string):
    """
    Find activity from the arg_string from a macro. Return error message string if it can't be found.
    """
    act_name = arg_string.strip()
    attrs = {}
    acts = Activity.objects.filter(offering=offering, deleted=False).filter(
        models.Q(name=act_name) | models.Q(short_name=act_name))
    if len(acts) == 0:
        return u'[No activity "%s"]' % (act_name)
    elif len(acts) > 1:
        return u'[There is both a name and short name "%s"]' % (act_name)
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
            text = u'["%s" has no due date specified]' % (act.name)
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
