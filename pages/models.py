from django.db import models, transaction
from django.core.files.storage import FileSystemStorage
from django.conf import settings
from django.utils.safestring import mark_safe
from coredata.models import CourseOffering, Member

from jsonfield import JSONField
from courselib.json_fields import getter_setter
from autoslug import AutoSlugField
from courselib.slugs import make_slug
import creoleparser

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
            instance.activity.offering.slug,
            instance.activity.slug + "_marking",
            datetime.now().strftime("%Y-%m-%d-%H-%M-%S") + "_" + str(instance.created_by),
            filename.encode('ascii', 'ignore'))
    return fullpath


class Page(models.Model):
    """
    A page in this courses "web site". Actual data is versioned in PageVersion objects.
    """
    offering = models.ForeignKey(CourseOffering)
    title = models.CharField(max_length=60, help_text="The title for the page")
    label = models.CharField(max_length=30, help_text="The short label (&approx;filename) for the page")
    can_read = models.CharField(max_length=4, choices=READ_ACL_CHOICES, default="ALL", help_text="Who should be able to view this page?")
    can_write = models.CharField(max_length=4, choices=WRITE_ACL_CHOICES, default="STAF", help_text="Who should be able to edit this page?")    

    def autoslug(self):
        return make_slug(self.label)
    slug = AutoSlugField(populate_from=autoslug, null=False, editable=True, unique_with='offering')
    config = JSONField(null=False, blank=False, default={}) # addition configuration stuff:
      # p.config['math']: page uses MathJax? (boolean)
      # p.config['syntax']: page uses SyntaxHighlighter? (boolean)
      # p.config['brushes']: used SyntaxHighlighter brushes (list of strings)

    defaults = {'math': False, 'syntax': False, 'brushes': []}
    math, set_math = getter_setter('math')
    syntax, set_syntax = getter_setter('syntax')
    brushes, set_brushes = getter_setter('brushes')

    class Meta:
        ordering = ['offering', 'label']
        unique_together = (('offering', 'label'),('offering', 'title'),)
        
    def save(self, *args, **kwargs):
        self.slug = None
        super(Page, self).save(*args, **kwargs)
    
    def current_version(self):
        return PageVersion.objects.filter(page=self).latest('created_at')
    def current_html(self):
        return self.current_version().html_contents()

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

    created_at = models.DateTimeField(auto_now=True)
    editor = models.ForeignKey(Member)
    comment = models.TextField()
    
    def clean(self):
        """
        Make sure this is either a wiki page or a file (but not both).
        """
        pass
    
    @transaction.commit_manually
    def save(self, save_part=False, *args, **kwargs):
        # TODO: update previous PageVersion object now: remove wikitext and set diff/diff_from.
        super(PageVersion, self).save(*args, **kwargs)
        
        if not save_part:
            # Only commit is we're the top-level save action;
            # don't commit while saving previous PageVersion objects above.
            transaction.commit()

    def html_contents(self):
        return mark_safe(text2html(self.wikitext))




# custom creoleparser Parser class:
import re
class CodeBlock(creoleparser.elements.BlockElement):
    """
    A block of code that gets syntax-highlited
    """
    def __init__(self, tag, token):
        super(CodeBlock,self).__init__(tag,token)
        self.regexp = re.compile(self.re_string(),re.DOTALL+re.MULTILINE)
        self.regexp2 = re.compile(self.re_string2(),re.MULTILINE)

    def re_string(self):
        start = '^' + re.escape(self.token[0]) + r'(\w+)\s*?\n'
        content = r'(.+?\n)'
        end = re.escape(self.token[1]) + r'\s*?$'
        return start + content + end

    def re_string2(self):
        """Finds a closing token with a space at the start of the line."""
        return r'^ (\s*?' + re.escape(self.token[1]) + r'\s*?\n)'

    def _build(self,mo,element_store, environ):
        match = self.regexp2.sub(r'\1',mo.group(1))
        raise

        return bldr.tag.__getattr__(self.tag)(
            fragmentize(match,self.child_elements,
                        element_store, environ,remove_escapes=False))


CreoleBase = creoleparser.creole11_base()
class CreoleDialect(CreoleBase):
    codeblock = CodeBlock('pre',['[{[{','}]}]'])
    @property
    def block_elements(self):
        blocks = super(CreoleDialect, self).block_elements
        blocks.append(self.codeblock)
        return blocks

parser = creoleparser.core.Parser(CreoleDialect)
text2html = parser.render



