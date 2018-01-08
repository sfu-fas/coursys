from rest_framework import serializers
from coredata.models import Person
from grades.models import Activity
from grades.utils import generate_numeric_activity_stat, generate_letter_activity_stat
from marking.models import get_activity_mark_for_student
from marking.serializers import MarkDetailSerializer
from courselib.rest import utc_datetime

class ActivitySerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField(help_text='URL for more info, if set by instructor')
    max_grade = serializers.SerializerMethodField()
    is_numeric = serializers.ReadOnlyField()
    is_calculated = serializers.ReadOnlyField()

    class Meta:
        model = Activity
        fields = ('slug', 'name', 'short_name', 'due_date', 'percent', 'group', 'url', 'max_grade', 'is_numeric', 'is_calculated')

    def transform_due_date(self, obj, value):
        return utc_datetime(value)

    def get_url(self, a):
        return a.url() or None

    def get_max_grade(self, a):
        return getattr(a, 'max_grade', None)


class GradeMarkSerializer(serializers.Serializer):
    slug = serializers.SlugField(help_text='String that identifies this activity within the course offering')
    grade = serializers.SerializerMethodField(help_text='Grade the student received, or null')
    max_grade = serializers.SerializerMethodField(help_text='Maximum grade for numeric activities, or null for letter activities')
    comment = serializers.SerializerMethodField(help_text='Comment entered when marking, or null')
    details = MarkDetailSerializer(help_text='Marking details, if configured by instructor and received by this student.')

    def _get_grade(self, a):
        # annotate the activity with its grade and marking object before starting
        if hasattr(a, 'grade'):
            return

        a.grade = a.get_grade(self.context['view'].member.person, self.context['view'].member.role)

        if self.context['view'].member.role == 'STUD' and a.status != 'RLS':
            a.details = None
        else:
            a.details = get_activity_mark_for_student(a, self.context['view'].member)

    def get_grade(self, a):
        self._get_grade(a)
        if a.grade:
            return str(a.grade.grade)
        else:
            return None

    def get_comment(self, a):
        self._get_grade(a)
        if a.grade:
            return a.grade.comment
        else:
            return None

    def get_max_grade(self, a):
        return getattr(a, 'max_grade', None)


class StudentSerializer(serializers.ModelSerializer):
    emplid = serializers.SerializerMethodField()
    class Meta:
        model = Person
        fields = ('emplid', 'userid', 'first_name', 'last_name', 'pref_first_name', 'email')

    def get_emplid(self, p):
        return str(p.emplid)



class StatsSerializer(serializers.Serializer):
    slug = serializers.SlugField(help_text='String that identifies this activity within the course offering')
    count = serializers.SerializerMethodField(help_text='Grade count')
    min = serializers.SerializerMethodField(help_text='Minimum grade')
    max = serializers.SerializerMethodField(help_text='Maximum grade')
    average = serializers.SerializerMethodField(help_text='Average (mean) grade, or null for letter graded activities')
    median = serializers.SerializerMethodField(help_text='Median grade')
    histogram = serializers.SerializerMethodField(help_text='Histogram data: list of label/count pairs, null if not available or disabled by instructor')
    missing_reason = serializers.CharField(help_text='Human-readable reason stats are missing (if relevant)')

    def _get_stats(self, a):
        # annotate the activity with its stats object before starting
        if hasattr(a, 'stats'):
            return

        if a.is_numeric():
            a.stats, a.missing_reason = generate_numeric_activity_stat(a, self.context['view'].member.role)
        else:
            a.stats, a.missing_reason = generate_letter_activity_stat(a, self.context['view'].member.role)

    def _get_or_none(self, a, attr):
        self._get_stats(a)
        if a.stats:
            return getattr(a.stats, attr, None)
        else:
            return None

    def get_histogram(self, a):
        self._get_stats(a)
        if a.stats:
            return [(rng.grade_range, rng.stud_count) for rng in a.stats.grade_range_stat_list]
        else:
            return None

    def get_count(self, a):
        return self._get_or_none(a, 'count')

    def get_min(self, a):
        return self._get_or_none(a, 'min')

    def get_max(self, a):
        return self._get_or_none(a, 'max')

    def get_average(self, a):
        return self._get_or_none(a, 'average')

    def get_median(self, a):
        return self._get_or_none(a, 'median')
