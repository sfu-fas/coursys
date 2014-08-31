from rest_framework import serializers
from coredata.models import CourseOffering, Member
from grades.models import Activity
from courselib.rest import utc_datetime

class CourseOfferingSerializer(serializers.ModelSerializer):
    semester = serializers.Field(source='semester.name')
    url = serializers.Field(source='url')
    instructors = serializers.SerializerMethodField('get_instructors')
    tas = serializers.SerializerMethodField('get_tas')
    contact_email = serializers.Field(source='taemail')

    class Meta:
        model = CourseOffering
        fields = ('subject', 'number', 'section', 'semester', 'crse_id', 'class_nbr', 'title', 'campus', 'slug',
            'url', 'contact_email',
            'instructors', 'tas')

    def get_instructors(self, o):
        return [{'fname': p.real_pref_first(), 'lname': p.last_name, 'email': p.email()} for p in o.instructors()]

    def get_tas(self, o):
        return [{'fname': p.real_pref_first(), 'lname': p.last_name, 'email': p.email()} for p in o.tas()]


class ActivitySerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField('get_url')

    class Meta:
        model = Activity
        fields = ('name', 'short_name', 'slug', 'due_date', 'percent', 'group', 'url')

    def transform_due_date(self, obj, value):
        return utc_datetime(value)

    def get_url(self, a):
        url = a.url()
        return url or None
