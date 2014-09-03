from rest_framework import generics, views

from grades.models import all_activities_filter
from grades.serializers import ActivitySerializer, GradeMarkSerializer
from courselib.rest import APIConsumerPermissions, IsOfferingMember

class OfferingActivities(generics.ListAPIView):
    permission_classes = (APIConsumerPermissions, IsOfferingMember,)
    consumer_permissions = set(['courses'])

    serializer_class = ActivitySerializer

    def get_queryset(self):
        return all_activities_filter(self.offering)

class OfferingGrades(generics.GenericAPIView):
    permission_classes = (APIConsumerPermissions, IsOfferingMember,)
    consumer_permissions = set(['courses', 'grades'])

    serializer_class = GradeMarkSerializer

    def get_object(self):
        activities = all_activities_filter(offering=self.offering)
        activities = [a for a in activities if a.status in ['RLS', 'URLS']]
        for activity in activities:
            g = activity.display_grade_student(self.member.person)
            # ???
        return []
