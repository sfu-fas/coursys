import datetime

from pages.models import Page, PageVersion
from haystack import indexes


class PageIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True)
    #title = indexes.EdgeNgramField()
    url = indexes.CharField(indexed=False, null=False)
    search_display = indexes.CharField(indexed=False)
    permission_key = indexes.CharField(indexed=True)

    def get_model(self):
        return Page

    def index_queryset(self, using=None):
        cutoff = datetime.date.today() - datetime.timedelta(days=730)
        return self.get_model().objects.exclude(can_read='NONE').filter(offering__semester__start__gte=cutoff) \
            .select_related('offering')

    def should_update(self, p):
        # no PageVersion yet? Still mid-save, so ignore.
        try:
            p.current_version()
            return True
        except PageVersion.DoesNotExist:
            return False

    def prepare_text(self, p):
        v = p.current_version()
        title = v.title
        wikitext = v.get_wikitext()[:10000]
        return title + '\n' + wikitext

    def prepare_title(self, p):
        v = p.current_version()
        return v.title

    def prepare_search_display(self, p):
        v = p.current_version()
        return "%s: %s" % (p.offering.name(), v.title)

    def prepare_url(self, p):
        return p.get_absolute_url()

    def prepare_permission_key(self, p):
        # a string expressing who can read this page: used for permission checking in search
        acl_value = Page.adjust_acl_release(p.can_read, p.releasedate())
        if acl_value == 'ALL':
            perm = 'ALL'
        else:
            perm = "%s_%s" % (p.offering.slug, acl_value)
        return perm
