from django.db import models, transaction
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.utils.safestring import mark_safe
from coredata.models import CourseOffering, Member

from jsonfield import JSONField
from courselib.json_fields import getter_setter
from autoslug import AutoSlugField
from courselib.slugs import make_slug
import creoleparser, os, datetime

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
    label = models.CharField(max_length=30, help_text="The short label (&approx;filename) for the page")
    can_read = models.CharField(max_length=4, choices=READ_ACL_CHOICES, default="ALL",
        help_text="Who should be able to view this page?")
    can_write = models.CharField(max_length=4, choices=WRITE_ACL_CHOICES, default="STAF",
        verbose_name="Can change", help_text="Who should be able to edit this page?")    

    def autoslug(self):
        return make_slug(self.label)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=True, unique_with='offering')
    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff:

    class Meta:
        ordering = ['offering', 'label']
        unique_together = (('offering', 'label'),('offering', 'title'),)
        
    def save(self, *args, **kwargs):
        self.slug = None
        super(Page, self).save(*args, **kwargs)
    
    def current_version(self):
        return PageVersion.objects.filter(page=self).select_related('editor__person').latest('created_at')

class PageVersion(models.Model):
    """
    A particular revision of a Page's contents. Could be either a wiki page or a file attachment.
    """
    page = models.ForeignKey(Page)
    wikitext = models.TextField()
    diff = models.TextField()
    diff_from = models.ForeignKey('PageVersion', null=True)
    file_attachment = models.FileField(storage=PageFilesStorage, null=False, upload_to=attachment_upload_to, blank=False, max_length=500)
    file_mediatype = models.CharField(null=False, blank=False, max_length=200)
    file_name = models.CharField(null=False, blank=False, max_length=200)

    created_at = models.DateTimeField(auto_now=True)
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
    
    @transaction.commit_manually
    def save(self, save_part=False, *args, **kwargs):
        # TODO: update previous PageVersion object now: remove wikitext and set diff/diff_from.

        self.set_brushes([])
        if self.wikitext:
            brushes = brushes_used(parser.parse(self.wikitext))
            self.set_brushes(list(brushes))
            self.set_syntax(bool(brushes))

        super(PageVersion, self).save(*args, **kwargs)
        
        if not save_part:
            # Only commit is we're the top-level save action;
            # don't commit while saving previous PageVersion objects above.
            transaction.commit()

    def html_contents(self):
        return mark_safe(text2html(self.wikitext))




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
        super(CodeBlock,self).__init__('pre', ['[{','}]'])
        self.regexp = re.compile(self.re_string(), re.DOTALL+re.MULTILINE)
        self.regexp2 = re.compile(self.re_string2(), re.MULTILINE)

    def re_string(self):
        start = '^\[\{\s*?(' + brushre + ')\s*?\n'
        content = r'(.+?\n)'
        end = r'\}\]\s*?$'
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
            



