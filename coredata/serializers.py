from django.urls import reverse
from rest_framework import serializers
from courselib.rest import HyperlinkCollectionField
from coredata.models import CourseOffering

class ShortCourseOfferingSerializer(serializers.ModelSerializer):
    semester = serializers.ReadOnlyField(source='semester.name', help_text='The SIMS-format semester for the offering')
    link = serializers.HyperlinkedIdentityField(view_name='api:OfferingInfo', lookup_field='slug',
        lookup_url_kwarg='course_slug', help_text='Link to more information for this offering')

    class Meta:
        model = CourseOffering
        fields = ('subject', 'number', 'section', 'semester', 'title', 'slug', 'link')


class CourseOfferingSerializer(ShortCourseOfferingSerializer):
    link_data = [
        {
            'label': 'activities',
            'view_name': 'api:OfferingActivities',
            'lookup_field': 'slug',
            'lookup_url_kwarg': 'course_slug',
        },
        {
            'label': 'grades',
            'view_name': 'api:OfferingGrades',
            'lookup_field': 'slug',
            'lookup_url_kwarg': 'course_slug',
        },
        {
            'label': 'stats',
            'view_name': 'api:OfferingStats',
            'lookup_field': 'slug',
            'lookup_url_kwarg': 'course_slug',
        },
        {
            'label': 'students',
            'view_name': 'api:OfferingStudents',
            'lookup_field': 'slug',
            'lookup_url_kwarg': 'course_slug',
        },
    ]
    url = serializers.ReadOnlyField(help_text='course homepage URL, if set by instructor')
    instructors = serializers.SerializerMethodField()
    tas = serializers.SerializerMethodField()
    contact_email = serializers.ReadOnlyField(source='taemail', help_text='Contact email for the TAs, if set by instructor')
    links = HyperlinkCollectionField(link_data, help_text='Links to additional information')

    class Meta(ShortCourseOfferingSerializer.Meta):
        model = CourseOffering
        fields = ('subject', 'number', 'section', 'semester', 'crse_id', 'class_nbr', 'title', 'campus', 'slug',
            'url', 'contact_email', 'instructors', 'tas', 'links')

    def get_instructors(self, o):
        return [{'fname': p.real_pref_first(), 'lname': p.last_name, 'email': p.email()} for p in o.instructors()]

    def get_tas(self, o):
        return [{'fname': p.real_pref_first(), 'lname': p.last_name, 'email': p.email()} for p in o.tas()]