from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework import generics

from coredata.models import Member
from coredata.serializers import CourseOfferingSerializer
from dashboard.views import _get_memberships
from courselib.rest import APIConsumerPermissions

class MyOfferings(generics.ListAPIView):
    permission_classes = (APIConsumerPermissions,)
    consumer_permissions = set(['courses'])

    serializer_class = CourseOfferingSerializer

    def get_queryset(self):
        memberships, _ = _get_memberships(self.request.user.username)
        offerings = [m.offering for m in memberships]
        return offerings

'''
class OfferingInfo(generics.RetrieveAPIView):
    permission_classes = (APIConsumerPermissions,)
    consumer_permissions = set(['courses'])

    serializer_class = CourseOfferingSerializer

    def get_object(self):
        member = get_object_or_404(Member, ~Q(role='DROP'), ~Q(offering__component='CAN'), offering__slug=self.kwargs['course_slug'],
                                   person__userid=self.request.user.username)
        return member.offering
'''