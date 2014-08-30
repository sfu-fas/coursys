from rest_framework import serializers
from coredata.models import CourseOffering


class CourseOfferingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseOffering
        fields = ('subject', 'number', 'section', 'semester', 'crse_id', 'class_nbr', 'title', 'campus', 'slug')

    def transform_semester(self, obj, value):
        if obj:
            return obj.semester.name
        else:
            return None