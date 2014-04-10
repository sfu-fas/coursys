from django.db import models
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.utils.safestring import mark_safe
from django.core.cache import cache
from django.core.urlresolvers import reverse
from coredata.models import CourseOffering, Member
from grades.models import Activity

from jsonfield import JSONField
from courselib.json_fields import getter_setter
import creoleparser, pytz
import os, datetime, re, difflib, json

WRITE_ACL_CHOICES = [
    ('NONE', 'nobody'),
    ('INST', 'instructor'),
    ('STAF', 'instructor and TAs'),
    ('STUD', 'students, instructor and TAs') ]
READ_ACL_CHOICES = WRITE_ACL_CHOICES + [('ALL', 'anybody')]
ACL_DESC = dict(READ_ACL_CHOICES)
WRITE_ACL_DESC = dict(WRITE_ACL_CHOICES)

MEMBER_ROLES = { # map from ACL roles to allowed Member roles
        'NONE': set(),
        'INST': set(['APPR', 'INST']),
        'STAF': set(['APPR', 'INST', 'TA']),
        'STUD': set(['APPR', 'INST', 'TA', 'STUD']),
        'ALL':  set(['APPR', 'INST', 'TA', 'STUD', 'DROP']),
        }
ACL_ROLES = { # reverse of MEMBER_ROLES: what ACLs is this Member allowed to access?
        'APPR': set(['INST', 'STAF', 'STUD', 'ALL']),
        'INST': set(['INST', 'STAF', 'STUD', 'ALL']),
        'TA': set(['STAF', 'STUD', 'ALL']),
        'STUD': set(['STUD', 'ALL']),
        'DROP': set(['ALL']),
        }

label_re = re.compile("^[\w\-_\.]+$")

PageFilesStorage = FileSystemStorage(location=settings.SUBMISSION_PATH, base_url=None)
def attachment_upload_to(instance, filename):
    """
    callback to avoid path in the filename(that we have append folder structure to) being striped 
    """
    fullpath = os.path.join(
            instance.page.offering.slug,
            "pagefiles", 
            datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + "_" + str(instance.editor.person.userid),
            filename.encode('ascii', 'ignore'))
    return fullpath


class Page(models.Model):
    """
    A page in this courses "web site". Actual data is versioned in PageVersion objects.
    """
    offering = models.ForeignKey(CourseOffering)
    label = models.CharField(max_length=30, db_index=True, help_text="The &ldquo;filename&rdquo; for this page")
    can_read = models.CharField(max_length=4, choices=READ_ACL_CHOICES, default="ALL",
        help_text="Who should be able to view this page?")
    can_write = models.CharField(max_length=4, choices=WRITE_ACL_CHOICES, default="STAF",
        verbose_name="Can change", help_text="Who should be able to edit this page?")
    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff:
        # p.config['releasedate']: date after which is page is visible
        # p.config['editdate']: date after which is page is editable
    
    defaults = {'releasedate': None, 'editdate': None}
    releasedate_txt, set_releasedate_txt = getter_setter('releasedate')
    editdate_txt, set_editdate_txt = getter_setter('editdate')

    class Meta:
        ordering = ['label']
        unique_together = (('offering', 'label'), )
    
    def save(self, *args, **kwargs):
        assert self.label_okay(self.label) is None
        super(Page, self).save(*args, **kwargs)

    def releasedate(self):
        d = self.releasedate_txt()
        if d is None:
            return None
        else:
            return datetime.datetime.strptime(d, "%Y-%m-%d").date()
    def editdate(self):
        d = self.editdate_txt()
        if d is None:
            return None
        else:
            return datetime.datetime.strptime(d, "%Y-%m-%d").date()
    def set_releasedate(self, val):
        if isinstance(val, datetime.date):
            val = val.strftime("%Y-%m-%d")
        self.set_releasedate_txt(val)
    def set_editdate(self, val):
        if isinstance(val, datetime.date):
            val = val.strftime("%Y-%m-%d")
        self.set_editdate_txt(val)
            

    def get_absolute_url(self):
        if self.label == 'Index':
            return reverse('pages.views.index_page', kwargs={'course_slug': self.offering.slug})
        else:
            return reverse('pages.views.view_page', kwargs={'course_slug': self.offering.slug, 'page_label': self.label})
    def version_cache_key(self):
        return "page-curver-" + str(self.id)
    def label_okay(self, label):
        """
        Check to make sure this label is acceptable (okay characters)
        
        Used by both self.save() and model validator.
        """
        m = label_re.match(label)
        if not m:
            return "Labels can contain only letters, numbers, underscores, dashes, and periods."
    
    def __unicode__(self):
        return self.offering.name() + '/' + self.label
    
    def current_version(self):
        """
        The most recent PageVersion object for this Page
        
        Cached to save the frequent lookup.
        """
        key = self.version_cache_key()
        v = cache.get(key)
        if v:
            return v
        else:
            v = PageVersion.objects.filter(page=self).select_related('editor__person').latest('created_at')
            cache.set(key, v, 3600) # expired when a PageVersion is saved
            return v

    @classmethod
    def adjust_acl_release(cls, acl_value, date):
        """
        Adjust the access control value appropriately, taking the release date into account.
        """
        if not date:
            # no release date, so nothing to do.
            return acl_value
        elif date and datetime.date.today() >= date:
            # release date passed: nothing to do.
            return acl_value
        else:
            # release date hasn't passed: upgrade the security level accordingly.
            if acl_value == 'NONE':
                return 'NONE'
            elif acl_value == 'STAF':
                return 'INST'
            else:
                return 'STAF'

    def release_message(self):
        return self._release_message(self.releasedate(), self.can_read, "viewable")
    def _release_message(self, date, acl_value, attrib):
        today = datetime.date.today()
        if not date:
            return None
        elif date > today:
            return "This page has not yet been released. It will be %s by %s as of %s." % (attrib, ACL_DESC[acl_value], date)
        else:
            #return "This page was made %s automatically on %s." % (attrib, date)
            return None


class PageVersion(models.Model):
    """
    A particular revision of a Page's contents. Could be either a wiki page or a file attachment.
    """
    page = models.ForeignKey(Page)
    title = models.CharField(max_length=60, help_text="The title for the page")
    wikitext = models.TextField(help_text='WikiCreole-formatted content of the page')
    diff = models.TextField(null=True, blank=True)
    diff_from = models.ForeignKey('PageVersion', null=True)
    file_attachment = models.FileField(storage=PageFilesStorage, null=False, upload_to=attachment_upload_to, blank=False, max_length=500)
    file_mediatype = models.CharField(null=False, blank=False, max_length=200)
    file_name = models.CharField(null=False, blank=False, max_length=200)

    created_at = models.DateTimeField(auto_now_add=True)
    editor = models.ForeignKey(Member)
    comment = models.TextField()

    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff:
        # p.config['math']: page uses MathJax? (boolean)
        # p.config['syntax']: page uses SyntaxHighlighter? (boolean)
        # p.config['brushes']: used SyntaxHighlighter brushes (list of strings)
        # p.config['depth']: max depth of diff pages below me (to keep it within reason)
    
    defaults = {'math': False, 'syntax': False, 'brushes': [], 'depth': 0}
    math, set_math = getter_setter('math')
    syntax, set_syntax = getter_setter('syntax')
    brushes, set_brushes = getter_setter('brushes')
    depth, set_depth = getter_setter('depth')

    def html_cache_key(self):
        return "page-html-" + str(self.id)
    def wikitext_cache_key(self):
        return "page-wikitext-" + str(self.id)
    
    def get_wikitext(self):
        """
        Return this version's wikitext (reconstructing from diffs if necessary).
        
        Caches when reconstructing from diffs
        """
        if self.diff_from:
            key = self.wikitext_cache_key()
            wikitext = cache.get(key)
            if wikitext:
                return wikitext
            else:
                src = self.diff_from
                diff = json.loads(self.diff)
                wikitext = src.apply_changes(diff)
                cache.set(key, wikitext, 24*3600) # no need to expire: shouldn't change for a version
                return wikitext

        return self.wikitext
    
    def __init__(self, *args, **kwargs):
        super(PageVersion, self).__init__(*args, **kwargs)
        self.Creole = None
    
    def get_creole(self):
        if not self.Creole:
            self.Creole = ParserFor(self.page.offering, self)
    
    def previous_version(self):
        """
        Return the version before this one, or None
        """
        try:
            prev = PageVersion.objects.filter(page=self.page,
                   created_at__lt=self.created_at).latest('created_at')
            return prev
        except PageVersion.DoesNotExist:
            return None

    def changes(self, other):
        """
        Changes to get from the get_wikitext() of self to other.
        
        List of changes that can be insertions, deletions, or replacements. Each
        is a tuple containing:
          (type flag, position of change, [other info need to reconstrut original])
        """
        lines1 = self.get_wikitext().split("\n")
        lines2 = other.get_wikitext().split("\n")
        
        matcher = difflib.SequenceMatcher()
        matcher.set_seqs(lines1, lines2)
        
        changes = []
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # ignore no-change blocks
                pass
            elif tag == 'insert':
                changes.append(("I", i1, lines2[j1:j2]))
            elif tag == 'delete':
                changes.append(("D", i1, i2))
            elif tag == 'replace':
                changes.append(("R", i1, i2, lines2[j1:j2]))
            else:
                raise ValueError
        
        return changes

    def apply_changes(self, changes):
        """
        Apply changes to this wikitext
        """
        lines = self.get_wikitext().split("\n")
        # sort by reverse linenumber: make sure we make changes in the right place
        changes.sort(cmp=lambda x,y: cmp(y[1], x[1]))
        
        for change in changes:
            c = change[0]
            if c=="I":
                _, pos, ls = change
                lines[pos:pos] = ls
            elif c=="D":
                _, pos1, pos2 = change
                del lines[pos1:pos2]
            elif c=="R":
                _, pos1, pos2, ls = change
                lines[pos1:pos2] = ls
            else:
                raise ValueError

        return "\n".join(lines)

    
    def diff_to(self, other):
        """
        Turn this version into a diff based on the other version (if apprpriate).
        """
        if not self.wikitext or self.diff_from:
            # must already be a diff: don't repeat ourselves
            return
        if self.depth() > 10:
            # don't let the chain of diffs get too long
            return
                
        oldw = self.wikitext

        diff = json.dumps(other.changes(self), separators=(',',':'))
        if len(diff) > len(oldw):
            # if it's a big change, don't bother.
            return

        self.diff = diff
        self.diff_from = other
        self.wikitext = ''
        self.save(check_diff=False) # save but don't go back for more diffing

        other.set_depth(max(self.depth()+1, other.depth()))
        other.save(minor_change=True)

        neww = self.get_wikitext()
        assert oldw==neww

    def save(self, check_diff=True, minor_change=False, *args, **kwargs):
        # check coherence of the data model: exactly one of full text, diff text, file.
        if not minor_change:
            # minor_change flag set when .diff_to has changed the .config only
            has_wikitext = bool(self.wikitext)
            has_difffrom = bool(self.diff_from)
            has_diff = bool(self.diff)
            has_file = bool(self.file_attachment)
            assert (has_wikitext and not has_difffrom and not has_diff and not has_file) \
                or (not has_wikitext and has_difffrom and has_diff and not has_file) \
                or (not has_wikitext and not has_difffrom and not has_diff and has_file)
        
            # normalize newlines so our diffs are consistent later
            self.wikitext = _normalize_newlines(self.wikitext)
        
            # set the SyntaxHighlighter brushes used on this page.
            self.set_brushes([])
            wikitext = self.get_wikitext()
            if wikitext:
                self.get_creole()
                brushes = brushes_used(self.Creole.parser.parse(wikitext))
                self.set_brushes(list(brushes))
                self.set_syntax(bool(brushes))

        super(PageVersion, self).save(*args, **kwargs)
        # update the *previous* PageVersion so it's a diff instead of storing full text
        if check_diff and not minor_change:
            prev = self.previous_version()
            if prev:
                prev.diff_to(self)

        # invalidate cache for all pages in this offering: makes sure current page, and all <<filelist>> are up to date
        for pv in PageVersion.objects.filter(page__offering=self.page.offering):
            key = pv.html_cache_key()
            cache.delete(key)
        # other cache cleanup
        cache.delete(self.wikitext_cache_key())
        cache.delete(self.page.version_cache_key())
        


    def __unicode__(self):
        return unicode(self.page) + '@' + unicode(self.created_at)

    def is_filepage(self):
        """
        Is this PageVersion a file attachment (as opposed to a Wiki page)?
        """
        return bool(self.file_attachment)
    def html_contents(self):
        """
        Return the HTML version of this version's wikitext.
        
        Cached to save frequent conversion.
        """
        key = self.html_cache_key()
        html = cache.get(key)
        if html:
            return mark_safe(html)
        else:
            self.get_creole()
            html = self.Creole.text2html(self.get_wikitext())
            cache.set(key, html, 24*3600) # expired if activities are changed (in signal below), or by saving a PageVersion in this offering
            return mark_safe(html)
        


# from http://code.activestate.com/recipes/435882-normalizing-newlines-between-windowsunixmacs/
_newlines_re = re.compile(r'(\r\n|\r|\r)')
def _normalize_newlines(string):
    return _newlines_re.sub('\n', string)


# signal for cache invalidation
def clear_offering_cache(instance, **kwargs):
    """
    Saving an activity might change HTML contents of any PageVersion, since they might
    contain <<duedate>> macros: invalidate all cached copies to be safe.
    """
    if not isinstance(instance, Activity):
        return
    if not hasattr(instance, 'offering'):
        # doesn't have an offering set yet: can't be a problem. Right?
        return

    for pv in PageVersion.objects.filter(page__offering=instance.offering):
        key = pv.html_cache_key()
        cache.delete(key)

models.signals.post_save.connect(clear_offering_cache)



# custom creoleparser Parser class:

import genshi
from brush_map import brush_code

brushre = r"[\w\-#]+"
brush_class_re = re.compile(r'brush:\s+(' + brushre + ')')

class AbbrAcronym(creoleparser.elements.InlineElement):
    # handles a subset of the abbreviation/acronym extension
    # http://www.wikicreole.org/wiki/AbbreviationAndAcronyms
    def __init__(self):
        super(AbbrAcronym,self).__init__('abbr', ['^','^'])

    def _build(self,mo,element_store, environ):
        try:
            abbr, title = mo.group(1).split(":", 1)
        except ValueError:
            abbr = mo.group(1)
            title = None
        return creoleparser.core.bldr.tag.__getattr__('abbr')(
                   creoleparser.core.fragmentize(abbr,
                       self.child_elements,
                       element_store, environ), title=title)


class CodeBlock(creoleparser.elements.BlockElement):
    """
    A block of code that gets syntax-highlited
    """
    def __init__(self):
        super(CodeBlock,self).__init__('pre', ['{{{','}}}'])
        self.regexp = re.compile(self.re_string(), re.DOTALL+re.MULTILINE)
        self.regexp2 = re.compile(self.re_string2(), re.MULTILINE)

    def re_string(self):
        start = '^\{\{\{\s*\[(' + brushre + ')\]\s*\n'
        content = r'(.+?\n)'
        end = r'\}\}\}\s*?$'
        return start + content + end

    def re_string2(self):
        """Finds a closing token with a space at the start of the line."""
        return r'^ (\s*?\}\]\s*?\n)'

    def _build(self,mo,element_store, environ):
        lang = mo.group(1)
        code = mo.group(2).rstrip()
        
        return creoleparser.core.bldr.tag.__getattr__(self.tag)(
            creoleparser.core.fragmentize(code, self.child_elements,
                        element_store, environ, remove_escapes=False),
            class_="brush: "+lang)

local_tz = pytz.timezone(settings.TIME_ZONE)
def _duedate(offering, dateformat, macro, environ, *act_name):
    """
    creoleparser macro for due datetimes
    
    Must be created in a closure by ParserFor with offering set (since that
    doesn't come from the parser).
    """    
    act_name = macro['arg_string'].strip()
    attrs = {}
    acts = Activity.objects.filter(offering=offering, deleted=False).filter(models.Q(name=act_name) | models.Q(short_name=act_name))
    if len(acts) == 0:
        text = '[No activity "%s"]' % (act_name)
        attrs['class'] = 'empty'
    elif len(acts) > 1:
        text = '[There is both a name and short name "%s"]' % (act_name)
        attrs['class'] = 'empty'
    else:
        act = acts[0]
        due = act.due_date
        if not due:
            text = '["%s" has no due date specified]' % (act_name)
            attrs['class'] = 'empty'
        else:
            iso8601 = local_tz.localize(due).isoformat()
            text = act.due_date.strftime(dateformat)
            attrs['title'] = iso8601

    return creoleparser.core.bldr.tag.__getattr__('span')(text, **attrs)

def _pagelist(offering, pageversion, macro, environ, prefix=None):
    # all pages [with the given prefix] for this offering
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
        def pagelist_macro(macro, environ, prefix=None):
            return _pagelist(self.offering, self.pageversion, macro, environ, prefix)

        if self.offering:
            nb_macros = {
                     'duedate': duedate_macro,
                     'duedatetime': duedatetime_macro,
                     'pagelist': pagelist_macro,
                     }
        else:
            nb_macros = None
        CreoleBase = creoleparser.creole11_base(non_bodied_macros=nb_macros)

        class CreoleDialect(CreoleBase):
            codeblock = CodeBlock()
            abbracronym = AbbrAcronym()
            strikethrough = creoleparser.elements.InlineElement('del','--')
            
            def __init__(self):
                self.custom_elements = [self.abbracronym, self.strikethrough]
                super(CreoleDialect,self).__init__()
                
            @property
            def inline_elements(self):
                inline = super(CreoleDialect, self).inline_elements
                inline.append(self.abbracronym)
                inline.append(self.strikethrough)
                return inline

            @property
            def block_elements(self):
                blocks = super(CreoleDialect, self).block_elements
                blocks.insert(0, self.codeblock)
                return blocks
        
        self.parser = creoleparser.core.Parser(CreoleDialect)
        self.text2html = self.parser.render
        


def brushes_used(parse):
    """
	All SyntaxHighlighter brush code files used in this wikitext.
	"""
    res = set()
    if hasattr(parse, 'children'):
        # recurse
        for c in parse.children:
            res |= brushes_used(c)

    if isinstance(parse, genshi.builder.Element) and parse.tag == 'pre':
        cls = parse.attrib.get('class')
        if cls:
            m = brush_class_re.match(cls)
            if m:
                b = m.group(1)
                if b in brush_code:
                    res.add(brush_code[b])

    return res




