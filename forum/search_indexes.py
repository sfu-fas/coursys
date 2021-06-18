from haystack import indexes

from forum.models import Thread


class ThreadIndex(indexes.SearchIndex, indexes.Indexable):
    # things we search
    offering_slug = indexes.CharField(indexed=True, model_attr='post__offering__slug')
    text = indexes.EdgeNgramField(document=True)
    privacy = indexes.CharField(indexed=True, model_attr='privacy')  # must honour privacy for student searches
    status = indexes.CharField(indexed=True, model_attr='post__status')  # ... and status=='HIDD'

    # things we display in search results: we're storing enough to reasonably-replicate the "list of threads" display.
    number = indexes.IntegerField(indexed=False, model_attr='post__number')
    title = indexes.CharField(indexed=False, model_attr='title')
    url = indexes.CharField(indexed=False)
    visible_author = indexes.CharField(indexed=False)

    def get_model(self):
        return Thread

    def index_queryset(self, using=None):
        return self.get_model().objects.exclude(post__status='HIDD').select_related('post', 'post__offering').prefetch_related('reply_set')

    def prepare_text(self, thread):
        components = [
            thread.title,
            thread.post.content,  # indexing the raw markup here, for better or worse
            thread.post.visible_author_short()  # the name visible to everybody (not real name for privacy=='INST')
        ]
        components.extend([
            r.post.content  # also raw markup
            for r in thread.reply_set.exclude(post__status='HIDD').select_related('post')
        ])
        return '\n'.join(components)

    def prepare_url(self, thread):
        return thread.post.get_absolute_url()

    def prepare_visible_author(self, thread):
        return thread.post.visible_author_short()
