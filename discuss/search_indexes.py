from discuss.models import DiscussionTopic, DiscussionMessage
from haystack import indexes

'''
class DiscussionIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True)
    url = indexes.CharField(indexed=False, null=False)
    search_display = indexes.CharField(indexed=False)
    slug = indexes.CharField(model_attr='offering__slug')

    def get_model(self):
        return DiscussionTopic

    def index_queryset(self, using=None):
        return self.get_model().objects.exclude(status='HID').prefetch_related('discussionmessage_set')

    def prepare_text(self, d):
        pieces = [d.title, d.content]
        replies = d.discussionmessage_set.exclude(status='HID')
        pieces.extend(m.content for m in replies)
        return '\n'.join(pieces)

    def prepare_url(self, d):
        return d.get_absolute_url()

    def prepare_search_display(self, d):
        return "%s: %s" % (d.offering.name(), d.title)
'''
