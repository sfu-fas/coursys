from django.db import models, transaction
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.utils.safestring import mark_safe
from coredata.models import CourseOffering, Member

from jsonfield import JSONField
from courselib.json_fields import getter_setter
import creoleparser
import os, datetime, re, difflib, json

WRITE_ACL_CHOICES = [
    ('NONE', 'nobody'),
    ('INST', 'instructor'),
    ('STAF', 'instructor and TAs'),
    ('STUD', 'students and staff') ]
READ_ACL_CHOICES = WRITE_ACL_CHOICES + [('ALL', 'anybody')]

MEMBER_ROLES = { # map from ACL roles to allowed Member roles
        'NONE': set(),
        'INST': set(['APPR', 'INST']),
        'STAF': set(['APPR', 'INST', 'TA']),
        'STUD': set(['APPR', 'INST', 'TA', 'STUD']),
        'ALL': set(['APPR', 'INST', 'TA', 'STUD', 'DROP']),
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
    title = models.CharField(max_length=60, help_text="The title for the page")
    label = models.CharField(max_length=30, help_text="The &ldquo;filename&rdquo; for this page")
    can_read = models.CharField(max_length=4, choices=READ_ACL_CHOICES, default="ALL",
        help_text="Who should be able to view this page?")
    can_write = models.CharField(max_length=4, choices=WRITE_ACL_CHOICES, default="STAF",
        verbose_name="Can change", help_text="Who should be able to edit this page?")    
    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff:

    class Meta:
        ordering = ['offering', 'label']
        unique_together = (('offering', 'label'), )
    
    def save(self, *args, **kwargs):
        assert self.label_okay(self.label) is None
        super(Page, self).save(*args, **kwargs)
    
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
        return PageVersion.objects.filter(page=self).select_related('editor__person').latest('created_at')

class PageVersion(models.Model):
    """
    A particular revision of a Page's contents. Could be either a wiki page or a file attachment.
    """
    page = models.ForeignKey(Page)
    wikitext = models.TextField()
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
    
    defaults = {'math': False, 'syntax': False, 'brushes': []}
    math, set_math = getter_setter('math')
    syntax, set_syntax = getter_setter('syntax')
    brushes, set_brushes = getter_setter('brushes')

    def clean(self):
        """
        Make sure this is either a wiki page or a file (but not both).
        """
        pass
    
    def get_wikitext(self):
        """
        Return this version's wikitext (reconstructing from diffs if necessary).
        """
        if self.diff_from:
            src = self.diff_from
            diff = json.loads(self.diff)
            return src.apply_changes(diff)
        return self.wikitext
    
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
        Turn this version into a diff based on the other version.
        """
        if not self.wikitext:
            # must already be a diff: don't repeat ourselves
            return
        
        oldw = self.get_wikitext()

        diff = json.dumps(other.changes(self), separators=(',',':'))
        if len(diff) > len(oldw):
            # if it's a big change, don't bother.
            return

        self.diff = diff
        self.diff_from_id = other.id
        self.wikitext = ''
        self.save(check_diff=False) # save but don't go back for more diffing

        neww = self.get_wikitext()
        assert oldw==neww

    def save(self, check_diff=True, *args, **kwargs):
        # normalize newlines so our diffs are easier later
        self.wikitext = _normalize_newlines(self.wikitext)
        
        # set the SyntaxHighlighter brushes used on this page.
        self.set_brushes([])
        wikitext = self.get_wikitext()
        if wikitext:
            brushes = brushes_used(parser.parse(wikitext))
            self.set_brushes(list(brushes))
            self.set_syntax(bool(brushes))

        super(PageVersion, self).save(*args, **kwargs)
        
        # update the *previous* PageVersion so it's a diff instead of storing full text
        if check_diff:
            prev = self.previous_version()
            if prev:
                prev.diff_to(self)


    def __unicode__(self):
        return unicode(self.page) + '@' + unicode(self.created_at)

    def is_filepage(self):
        return bool(self.file_attachment)
    def html_contents(self):
        return mark_safe(text2html(self.get_wikitext()))


# from http://code.activestate.com/recipes/435882-normalizing-newlines-between-windowsunixmacs/
_newlines_re = re.compile(r'(\r\n|\r|\r)')
def _normalize_newlines(string):
    return _newlines_re.sub('\n', string)


# custom creoleparser Parser class:

import re
import genshi
from brush_map import brush_code

brushre = r"[\w\-#]+"
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


CreoleBase = creoleparser.creole11_base()
class CreoleDialect(CreoleBase):
    codeblock = CodeBlock()
    @property
    def block_elements(self):
        blocks = super(CreoleDialect, self).block_elements
        blocks.insert(0, self.codeblock)
        return blocks

parser = creoleparser.core.Parser(CreoleDialect)
text2html = parser.render

brush_re = re.compile(r'brush:\s+(' + brushre + ')')
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
            m = brush_re.match(cls)
            if m:
                b = m.group(1)
                if b in brush_code:
                    res.add(brush_code[b])

    return res
            



