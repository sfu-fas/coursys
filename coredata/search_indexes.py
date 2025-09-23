import datetime

from coredata.models import CourseOffering, Person, Member
from haystack import indexes


class OfferingIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True)
    title = indexes.EdgeNgramField(model_attr='title')
    name = indexes.CharField(indexed=False)
    url = indexes.CharField(indexed=False, null=False)
    slug = indexes.CharField(model_attr='slug')
    search_display = indexes.CharField(indexed=False)

    def get_model(self):
        return CourseOffering

    def index_queryset(self, using=None):
        cutoff = datetime.date.today() - datetime.timedelta(days=3650)
        return self.get_model().objects.exclude(component='CAN').filter(semester__start__gte=cutoff).select_related('semester')

    def update_filter(self, qs):
        cutoff = datetime.date.today() - datetime.timedelta(days=365)
        return qs.filter(semester__start__gte=cutoff)

    def prepare_text(self, o):
        fields = [o.subject, o.number, o.section, o.title, o.instructors_str(), o.semester.name,
                  o.semester.label(), o.get_campus_display()]
        return '\n'.join(fields)

    def prepare_name(self, o):
        return ' '.join([o.subject, o.number, o.section])

    def prepare_url(self, o):
        return o.get_absolute_url()

    def prepare_search_display(self, o):
        return "%s %s" % (o.name(), o.semester.label())


class PersonIndex(indexes.SearchIndex, indexes.Indexable):
    # used for autocompletes, not full-site search
    text = indexes.EdgeNgramField(document=True)
    emplid = indexes.CharField(model_attr='emplid')
    search_display = indexes.CharField(indexed=False)

    def get_model(self):
        return Person

    def index_queryset(self, using=None):
        return self.get_model().objects.all()

    def prepare_text(self, o):
        fields = [str(o.emplid), o.first_name, o.last_name]
        if o.real_pref_first() != o.first_name:
            fields.append(o.real_pref_first())
        if 'legal_first_name_do_not_use' in o.config:
            # if the person has a legal first name stored, include it for searching, but it will still never be displayed by the system
            fields.append(o.config['legal_first_name_do_not_use'])
        if o.userid:
            fields.append(o.userid)
        return '\n'.join(fields)

    def prepare_search_display(self, o):
        return o.search_label_value()


class MemberIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.EdgeNgramField(document=True)
    offering_slug = indexes.CharField(null=False)
    url = indexes.CharField(indexed=False, null=False)
    search_display = indexes.CharField(indexed=False)
    role = indexes.CharField(indexed=False, model_attr='role') # student or TA?

    def get_model(self):
        return Member

    def index_queryset(self, using=None):
        # experimenally, two years worth of Members is the largest big-ugly-query our database in reasonable time
        cutoff = datetime.date.today() - datetime.timedelta(days=365*2)
        return self.get_model().objects.exclude(offering__component='CAN') \
                .filter(role__in=['STUD', 'TA']) \
                .select_related('person', 'offering__semester') \
                .filter(offering__semester__start__gte=cutoff)

    def update_filter(self, qs):
        cutoff = datetime.date.today() - datetime.timedelta(days=365)
        return qs.filter(offering__semester__start__gte=cutoff)

    def prepare_text(self, m):
        fields = [m.offering.semester.label(), m.offering.semester.name, m.offering.name(),
                  str(m.person.emplid), m.person.first_name, m.person.last_name]
        if m.person.real_pref_first() != m.person.first_name:
            fields.append(m.person.real_pref_first())
        if 'legal_first_name_do_not_use' in m.person.config:
            # if the person has a legal first name stored, include it for searching, but it will still never be displayed by the system
            fields.append(m.person.config['legal_first_name_do_not_use'])
        if m.person.userid:
            fields.append(m.person.userid)
        return '\n'.join(fields)

    def prepare_offering_slug(self, m):
        return m.offering.slug

    def prepare_url(self, m):
        if m.role == 'STUD':
            return m.get_absolute_url()
        elif m.role == 'TA':
            return m.offering.get_absolute_url()
        else:
            return None

    def prepare_search_display(self, m):
        return " %s (%s) in %s (%s)" % (m.person.name(), m.person.userid_or_emplid(), m.offering.name(), m.offering.semester.label())
