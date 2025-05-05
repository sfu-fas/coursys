from django.db import models, transaction
from django.conf import settings
from django.utils.safestring import mark_safe
from django.core.cache import cache
from django.urls import reverse
from coredata.models import CourseOffering, Member, Person
from grades.models import Activity

from courselib.json_fields import JSONField
from courselib.json_fields import getter_setter
from courselib.text import normalize_newlines
from courselib.storage import UploadedFileStorage, upload_path
from courselib.markup import markup_to_html, ensure_sanitary_markup
import pytz
import os, datetime, re, difflib, json, uuid

WRITE_ACL_CHOICES = [
    ('NONE', 'nobody'),
    ('INST', 'instructor'),
    ('STAF', 'instructor and TAs'),
    ('STUD', 'students, instructor and TAs') ]
READ_ACL_CHOICES = WRITE_ACL_CHOICES + [('ALL', 'anybody')]
ACL_DESC = dict(READ_ACL_CHOICES)
WRITE_ACL_DESC = dict(WRITE_ACL_CHOICES)

PERMISSION_ACL_CHOICES = WRITE_ACL_CHOICES[1:] # allowed permissions for PagePermission object

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

MACRO_LABEL = 'MACROS' # special page that contain macro expansions for other pages

label_re = re.compile(r"^[\w\-_\.]+$")
macroline_re = re.compile(r"^(?P<key>\w+):\s*(?P<value>.*)\s*$")


def attachment_upload_to(instance, filename):
    return upload_path(instance.page.offering.slug, '_pagefiles', filename)


class Page(models.Model):
    """
    A page in this courses "web site". Actual data is versioned in PageVersion objects.
    """
    offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT)
    label = models.CharField(max_length=30, db_index=True, help_text="The &ldquo;filename&rdquo; for this page")
    can_read = models.CharField(max_length=4, choices=READ_ACL_CHOICES, default="ALL",
        help_text="Who should be able to view this page?")
    can_write = models.CharField(max_length=4, choices=WRITE_ACL_CHOICES, default="STAF",
        verbose_name="Can change", help_text="Who should be able to edit this page?")
    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff:
        # p.config['releasedate']: date after which is page is visible
        # p.config['editdate']: date after which is page is editable
        # p.config['migrated_to']: if this page was migrated to a new location, the new (offering.slug, page.label)
        # p.config['migrated_from']: if this page was migrated from an old location, the old (offering.slug, page.label)
        # p.config['prevent_redirect']: if True, don't do a redirect, even if migration settings look like it should.

    defaults = {'releasedate': None, 'editdate': None}
    releasedate_txt, set_releasedate_txt = getter_setter('releasedate')
    editdate_txt, set_editdate_txt = getter_setter('editdate')

    class Meta:
        ordering = ['label']
        unique_together = (('offering', 'label'), )
    
    def save(self, *args, **kwargs):
        assert self.label_okay(self.label) is None
        self.expire_offering_cache()
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
            return reverse('offering:pages:index_page', kwargs={'course_slug': self.offering.slug})
        else:
            return reverse('offering:pages:view_page', kwargs={'course_slug': self.offering.slug, 'page_label': self.label})

    def version_cache_key(self):
        return "page-curver-" + str(self.id)

    def macro_cache_key(self):
        return "MACROS-" + str(self.offering_id)

    def expire_offering_cache(self):
        # invalidate cache for all pages in this offering: makes sure current page, and all <<filelist>> are up to date
        for pv in PageVersion.objects.filter(page__offering=self.offering):
            cache.delete(pv.html_cache_key())
            cache.delete(pv.wikitext_cache_key())
        # other cache cleanup
        cache.delete(self.version_cache_key())
        cache.delete(self.macro_cache_key())

    def label_okay(self, label):
        """
        Check to make sure this label is acceptable (okay characters)
        
        Used by both self.save() and model validator.
        """
        m = label_re.match(label)
        if not m:
            return "Labels can contain only letters, numbers, underscores, dashes, and periods."
    
    def __str__(self):
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
            cache.set(key, v, 24*3600) # expired when a PageVersion is saved
            return v

    @staticmethod
    def adjust_acl_release(acl_value, date):
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
    page = models.ForeignKey(Page, blank=True, null=True, on_delete=models.PROTECT)
    title = models.CharField(max_length=60, help_text="The title for the page")
    wikitext = models.TextField(help_text='Markup content of the page', verbose_name='Content')
    diff = models.TextField(null=True, blank=True)
    diff_from = models.ForeignKey('PageVersion', null=True, on_delete=models.PROTECT)
    file_attachment = models.FileField(storage=UploadedFileStorage, null=False, upload_to=attachment_upload_to, blank=False, max_length=500)
    file_mediatype = models.CharField(null=False, blank=False, max_length=200)
    file_name = models.CharField(null=False, blank=False, max_length=200)
    redirect = models.CharField(null=True, blank=True, max_length=500) # URL to redirect to: may be an absolute URL or relative from the location of self.page

    created_at = models.DateTimeField(auto_now_add=True)
    editor = models.ForeignKey(Member, on_delete=models.PROTECT)
    comment = models.TextField()

    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff:
        # p.config['markup']: markup language used: see courselib/markup.py
        # p.config['math']: page uses MathJax? (boolean)
        # p.config['syntax']: page uses SyntaxHighlighter? (boolean) -- no longer used with highlight.js
        # p.config['brushes']: used SyntaxHighlighter brushes (list of strings) -- no longer used with highlight.js
        # p.config['depth']: max depth of diff pages below me (to keep it within reason)
        # p.config['redirect_reason']: if present, how this redirect got here: 'rename' or 'delete'.

    defaults = {
        'math': False, 'depth': 0, 'redirect_reason': None, 'markup': 'creole',
    }
    markup, set_markup = getter_setter('markup')
    math, set_math = getter_setter('math')
    #syntax, set_syntax = getter_setter('syntax')
    #brushes, set_brushes = getter_setter('brushes')
    depth, set_depth = getter_setter('depth')
    redirect_reason, set_redirect_reason = getter_setter('redirect_reason')

    def html_cache_key(self):
        return "page-html-" + str(self.id)
    def wikitext_cache_key(self):
        return "page-wikitext-" + str(self.id)

    def get_wikitext(self):
        """
        Return this version's markup (reconstructing from diffs if necessary).
        
        Caches when reconstructing from diffs
        """
        if self.diff_from:
            key = self.wikitext_cache_key()
            wikitext = cache.get(key)
            if wikitext:
                return str(wikitext)
            else:
                src = self.diff_from
                diff = json.loads(self.diff)
                wikitext = src.apply_changes(diff)
                cache.set(key, wikitext, 24*3600) # no need to expire: shouldn't change for a version
                return str(wikitext)

        return str(self.wikitext)

    def __init__(self, *args, **kwargs):
        super(PageVersion, self).__init__(*args, **kwargs)

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
        changes.sort(key=lambda x: -x[1])
        
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
        # check coherence of the data model: exactly one of full text, diff text, file, redirect.
        if not minor_change:
            # minor_change flag set when .diff_to has changed the .config only
            has_wikitext = bool(self.wikitext)
            has_difffrom = bool(self.diff_from)
            has_diff = bool(self.diff)
            has_file = bool(self.file_attachment)
            has_redirect = bool(self.redirect)
            assert (has_wikitext and not has_difffrom and not has_diff and not has_file and not has_redirect) \
                or (not has_wikitext and has_difffrom and has_diff and not has_file and not has_redirect) \
                or (not has_wikitext and not has_difffrom and not has_diff and has_file and not has_redirect) \
                or (not has_wikitext and not has_difffrom and not has_diff and not has_file and has_redirect)
        
            # normalize newlines so our diffs are consistent later
            self.wikitext = normalize_newlines(self.wikitext)

        self.wikitext = ensure_sanitary_markup(self.wikitext, self.markup(), restricted=False)

        super(PageVersion, self).save(*args, **kwargs)
        # update the *previous* PageVersion so it's a diff instead of storing full text
        if check_diff and not minor_change:
            prev = self.previous_version()
            if prev:
                prev.diff_to(self)

        self.page.expire_offering_cache()

    def __str__(self):
        return str(self.page) + '@' + str(self.created_at)

    def is_filepage(self):
        """
        Is this PageVersion a file attachment (as opposed to a Wiki page)?
        """
        return bool(self.file_attachment)

    @staticmethod
    def _offering_macros(offering):
        """
        Do the actual work of constructing the macro dict for this offering
        """
        try:
            pv = PageVersion.objects.filter(page__offering=offering, page__label=MACRO_LABEL).latest('created_at')
        except PageVersion.DoesNotExist:
            return {}

        macros = {}
        for line in pv.get_wikitext().splitlines(True):
            m = macroline_re.match(line)
            if m:
                macros[m.group('key')] = m.group('value')
        return macros

    def offering_macros(self):
        """
        Return a dict of macros for this page's offering (caches _offering_macros).
        """
        if not self.page:
            return {}
        offering = self.page.offering
        key = self.page.macro_cache_key()
        macros = cache.get(key)
        if macros is not None:
            return macros
        else:
            macros = PageVersion._offering_macros(offering)
            cache.set(key, macros, 24*3600) # expired when a page is saved
            return macros

    def substitute_macros(self, wikitext):
        """
        Substitute our macros into the wikitext.
        """
        macros = self.offering_macros()
        if macros:
            for macro, replacement in macros.items():
                wikitext = wikitext.replace('+' + macro + '+', replacement)
        return wikitext

    def html_contents(self, offering=None):
        """
        Return the HTML version of this version's wikitext (with macros substituted if available)

        offering argument only required if self.page isn't set: used when doing a speculative conversion of unsaved content.
        
        Cached to save frequent conversion.
        """
        key = self.html_cache_key()
        html = cache.get(key)
        if html:
            return mark_safe(html)
        else:
            markup_content = self.substitute_macros(self.get_wikitext())
            html = markup_to_html(markup_content, self.markup(), pageversion=self, html_already_safe=True, hidden_llm=True)
            cache.set(key, html, 24*3600) # expired if activities are changed (in signal below), or by saving a PageVersion in this offering
            return mark_safe(html)


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


class PagePermission(models.Model):
    """
    An additional person who has permission to view pages for this offering
    """
    offering = models.ForeignKey(CourseOffering, on_delete=models.PROTECT)
    person = models.ForeignKey(Person, on_delete=models.PROTECT)
    role = models.CharField(max_length=4, choices=PERMISSION_ACL_CHOICES, default="STUD",
        help_text="What level of access should this person have for the course?")
    config = JSONField(null=False, blank=False, default=dict) # addition configuration stuff:

    defaults = {}

    class Meta:
        unique_together = (('offering', 'person'), )

    def get_role_display(self):
        if self.role == 'STUD':
            return 'student-equivalent'
        elif self.role == 'STAF':
            return 'TA-equivalent'
        else:
            return ACL_DESC[self.role]
