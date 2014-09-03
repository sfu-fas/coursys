from rest_framework import serializers
from grades.models import Activity
from courselib.rest import utc_datetime

class ActivitySerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField('get_url', help_text='URL for more info, if set by instructor')
    max_grade = serializers.SerializerMethodField('get_max_grade')
    is_numeric = serializers.Field(source='is_numeric')
    is_calculated = serializers.Field(source='is_calculated')

    class Meta:
        model = Activity
        fields = ('name', 'short_name', 'due_date', 'percent', 'group', 'url', 'max_grade', 'is_numeric', 'is_calculated')

    def transform_due_date(self, obj, value):
        return utc_datetime(value)

    def get_url(self, a):
        return a.url() or None

    def get_max_grade(self, a):
        return getattr(a, 'max_grade', None)
