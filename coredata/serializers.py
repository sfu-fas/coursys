from rest_framework import serializers
from coredata.models import CourseOffering, Member


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


class StudentSerializer(serializers.ModelSerializer):
    semester = serializers.Field(source='semester.name')
    class Meta:
        model = Member
        #fields = ('subject', 'number', 'section', 'semester', 'crse_id', 'class_nbr', 'title', 'campus', 'slug')
