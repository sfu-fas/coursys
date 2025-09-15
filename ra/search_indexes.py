import datetime

from ra.models import RAAppointment, RARequest
from haystack import indexes

# Any additions here should be reflected in courselib.signals.SelectiveRealtimeSignalProcessor so reindexing happens

class RAIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True)
    url = indexes.CharField(indexed=False, null=False)
    search_display = indexes.CharField(indexed=False)

    def get_model(self):
        return RAAppointment

    def index_queryset(self, using=None):
        cutoff = datetime.date.today() - datetime.timedelta(days=5*365)
        return self.get_model().objects.exclude(deleted=True).filter(start_date__gte=cutoff) \
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
        if 'legal_first_name_do_not_use' in grad.person.config:
            # if the person has a legal first name stored, include it for searching, but it will still never be displayed by the system
            pieces.append(grad.person.config['legal_first_name_do_not_use'])

        return '\n'.join(pieces)

    def prepare_url(self, ra):
        return ra.get_absolute_url()

    def prepare_search_display(self, ra):
        return "%s hired by %s" % (ra.person.name(), ra.hiring_faculty.name())

class RARequestIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True)
    url = indexes.CharField(indexed=False, null=False)
    search_display = indexes.CharField(indexed=False)

    def get_model(self):
        return RARequest

    def index_queryset(self, using=None):
        return self.get_model().objects.exclude(deleted=True, complete=False) \
            .select_related('person', 'supervisor', 'unit')

    def prepare_text(self, ra):
        pieces = [
            ra.get_name(),
            ra.supervisor.name(),
            ra.get_projects(),
            ra.get_funds(),
            str(ra.total_pay),
            ra.unit.label,
            ra.unit.name,
        ]
        if ra.person and 'legal_first_name_do_not_use' in ra.person.config:
            # if the person has a legal first name stored, include it for searching, but it will still never be displayed by the system
            pieces.append(ra.person.config['legal_first_name_do_not_use'])

        return '\n'.join(pieces)

    def prepare_url(self, ra):
        return ra.get_absolute_url()

    def prepare_search_display(self, ra):
        return "%s hired by %s" % (ra.get_name(), ra.supervisor.name())
