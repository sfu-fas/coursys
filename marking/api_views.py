from django.http import Http404
from rest_framework import generics
from courselib.rest import APIConsumerPermissions, IsOfferingStaff
from grades.models import all_activities_filter

from .models import StudentActivityMark, GroupActivityMark
from .serializers import MarkingDetails

import itertools

class MarkingDetails(generics.ListAPIView):
    permission_classes = (APIConsumerPermissions, IsOfferingStaff,)
    consumer_permissions = set(['grades-write'])
    serializer_class = MarkingDetails

    def get_queryset(self):
        activities = all_activities_filter(self.offering, slug=self.kwargs['activity_slug'])
        if not activities:
            raise Http404()

        activity = activities[0]
        gams = GroupActivityMark.objects.filter(activity=activity).order_by('-created_at')
        sams = StudentActivityMark.objects.filter(activity=activity).order_by('-created_at')

        return itertools.chain(gams, sams)
