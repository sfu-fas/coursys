from .models import Visa
from haystack import indexes

class VisaIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True)
    url = indexes.CharField(indexed=False, null=False)
    search_display = indexes.CharField(indexed=False)

    def get_model(self):
        return Visa

    def index_queryset(self, using=None):
        return self.get_model().objects.exclude(hidden=True) \
            .select_related('person', 'unit')

    def prepare_text(self, visa):
        pieces = [
            visa.person.sortname(),
            str(visa.person.emplid),
            visa.unit.label,
            visa.status,
            visa.get_validity()
        ]
        return '\n'.join(pieces)

    def prepare_url(self, visa):
        return visa.get_absolute_url()

    def prepare_search_display(self, visa):
        return "Visa for %s" % (visa.person.sortname())