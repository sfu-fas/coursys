from ra.models import RAAppointment
from haystack import indexes

# Any additions here should be reflected in courselib.signals.SelectiveRealtimeSignalProcessor so reindexing happens

class RAIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True)
    url = indexes.CharField(indexed=False, null=False)
    search_display = indexes.CharField(indexed=False)

    def get_model(self):
        return RAAppointment

    def index_queryset(self, using=None):
        return self.get_model().objects.exclude(deleted=True) \
            .select_related('person', 'hiring_faculty', 'project', 'account', 'unit')

    def prepare_text(self, ra):
        pieces = [
            ra.person.name_with_pref(),
            ra.hiring_faculty.name_with_pref(),
            str(ra.project.project_number),
            str(ra.project.fund_number),
            str(ra.account.account_number),
            str(ra.account.position_number),
            str(ra.lump_sum_pay),
            ra.unit.label,
            ra.unit.name,
        ]
        return '\n'.join(pieces)

    def prepare_url(self, ra):
        return ra.get_absolute_url()

    def prepare_search_display(self, ra):
        return "%s hired by %s" % (ra.person.name(), ra.hiring_faculty.name())
