from rest_framework import generics, views, response

from grades.models import all_activities_filter
from grades.serializers import ActivitySerializer, GradeMarkSerializer
from courselib.rest import APIConsumerPermissions, IsOfferingMember

class OfferingActivities(generics.ListAPIView):
    permission_classes = (APIConsumerPermissions, IsOfferingMember,)
    consumer_permissions = set(['courses'])

    serializer_class = ActivitySerializer

    def get_queryset(self):
        activities = all_activities_filter(self.offering)
        # TODO: staff should see all
        activities = [a for a in activities if a.status in ['RLS', 'URLS']]
        return activities

class OfferingGrades(generics.GenericAPIView):
    permission_classes = (APIConsumerPermissions, IsOfferingMember,)
    consumer_permissions = set(['courses', 'grades'])

    #serializer_class = GradeMarkSerializer

    def get(self, request, *args, **kwargs):
        activities = all_activities_filter(offering=self.offering)
        # TODO: staff should see all
        activities = [a for a in activities if a.status in ['RLS', 'URLS']]
        res = []
        for activity in activities:
            g = activity.get_grade(self.member.person)
            maxgrade = getattr(activity, 'max_grade', None)
            res.append({'slug': activity.slug, 'grade': g, 'max_grade': maxgrade})
        return response.Response(res)

class OfferingStats(generics.GenericAPIView):
    permission_classes = (APIConsumerPermissions, IsOfferingMember,)
    consumer_permissions = set(['courses', 'grades'])

    def get(self, request, *args, **kwargs):
        activities = all_activities_filter(offering=self.offering)
        # TODO: staff should see all
        activities = [a for a in activities if a.status in ['RLS', 'URLS']]
