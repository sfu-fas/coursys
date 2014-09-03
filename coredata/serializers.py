from django.core.urlresolvers import reverse
from rest_framework import serializers
from coredata.models import CourseOffering
from grades.models import Activity
from courselib.rest import utc_datetime

class ShortCourseOfferingSerializer(serializers.ModelSerializer):
    semester = serializers.Field(source='semester.name')
    link = serializers.HyperlinkedIdentityField(view_name='api.OfferingInfo',
                                                slug_field='slug', slug_url_kwarg='course_slug')

    class Meta:
        model = CourseOffering
        fields = ('subject', 'number', 'section', 'semester', 'title', 'slug', 'link')


class CourseOfferingSerializer(ShortCourseOfferingSerializer):
    url = serializers.Field(source='url', help_text='course homepage URL, if set by instructor')
    instructors = serializers.SerializerMethodField('get_instructors')
    tas = serializers.SerializerMethodField('get_tas')
    contact_email = serializers.Field(source='taemail')

    class Meta(ShortCourseOfferingSerializer.Meta):
        model = CourseOffering
        fields = ('subject', 'number', 'section', 'semester', 'crse_id', 'class_nbr', 'title', 'campus', 'slug',
            'url', 'contact_email', 'instructors', 'tas')

    def get_instructors(self, o):
        return [{'fname': p.real_pref_first(), 'lname': p.last_name, 'email': p.email()} for p in o.instructors()]

    def get_tas(self, o):
        return [{'fname': p.real_pref_first(), 'lname': p.last_name, 'email': p.email()} for p in o.tas()]