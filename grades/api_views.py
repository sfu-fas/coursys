from rest_framework import generics

from grades.models import all_activities_filter
from grades.serializers import ActivitySerializer
from courselib.rest import APIConsumerPermissions, IsOfferingMember

class OfferingActivities(generics.ListAPIView):
    permission_classes = (APIConsumerPermissions, IsOfferingMember,)
    consumer_permissions = set(['courses'])

    serializer_class = ActivitySerializer

    def get_queryset(self):
        return all_activities_filter(self.offering)