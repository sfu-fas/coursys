from coredata.models import CourseOffering, Person
from haystack import indexes

class OfferingIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True)
    name = indexes.CharField()
    title = indexes.EdgeNgramField(model_attr='title')

    def get_model(self):
        return CourseOffering

    def index_queryset(self, using=None):
        return self.get_model().objects.exclude(component='CAN')

    def prepare_text(self, o):
        fields = [o.subject, o.number, o.section, o.title, o.instructors_str(), o.semester.name,
                  o.semester.label(), o.get_campus_display()]
        return '\n'.join(fields)

    def prepare_name(self, o):
        return ' '.join([o.subject, o.number, o.section])


class PersonIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True)

    def get_model(self):
        return Person

    def index_queryset(self, using=None):
        return self.get_model().objects.all()

    def prepare_text(self, o):
        fields = [unicode(o.emplid), o.first_name, o.last_name]
        if o.real_pref_first() != o.first_name:
            fields.append(o.real_pref_first())
        if o.userid:
            fields.append(o.userid)
        return '\n'.join(fields)
