from rest_framework import generics

from coredata.serializers import CourseOfferingSerializer
from dashboard.views import _get_memberships
from courselib.rest import APIPermissions

class MyOfferings(generics.ListAPIView):
    permission_classes = (APIPermissions,)
    required_permissions = set(['courses'])

    serializer_class = CourseOfferingSerializer

    def get_queryset(self):
        memberships, _ = _get_memberships(self.request.user.username)
        offerings = [m.offering for m in memberships]
        return offerings


