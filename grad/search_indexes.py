from .models import GradStudent
from haystack import indexes

class GradIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True)
    url = indexes.CharField(indexed=False, null=False)
    search_display = indexes.CharField(indexed=False)

    def get_model(self):
        return GradStudent

    def index_queryset(self, using=None):
        return self.get_model().objects \
            .select_related('person', 'program')

    def prepare_text(self, grad):
        if grad.start_semester:
            start_semester_name = grad.start_semester.name
            start_semester_label = grad.start_semester.label()
        else:
            start_semester_name = ""
            start_semester_label = ""
        pieces = [
            grad.person.sortname(),
            str(grad.person.emplid),
            grad.program.label, grad.program.unit.label,
            start_semester_name, start_semester_label,
        ]
        return '\n'.join(pieces)

    def prepare_url(self, grad):
        return grad.get_absolute_url()

    def prepare_search_display(self, grad):
        return "Grad for %s" % (grad.person.sortname())