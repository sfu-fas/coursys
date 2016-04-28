from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics
from courselib.rest import APIConsumerPermissions, IsOfferingStaff

from grades.models import Activity
from .models import SubmissionInfo, Text
from .serializers import SubmissionsSerializer

from itertools import chain
import datetime

class ActivitySubmissions(generics.ListAPIView):
    """
    Retrieve (text) submissions for this activity.

    Query string ?hours=n will limit to submissions within the last n hours.

    This endpoint is experimental: no guarantees are made on its stability or continued existence.
    """
    # Implicitly reflects multi-submit behaviour. All submissions by a student/group are returned.
    # Returns only Text submissions for now, because they're easy to serialize.

    permission_classes = (APIConsumerPermissions, IsOfferingStaff,)
    consumer_permissions = set(['submissions-read'])
    serializer_class = SubmissionsSerializer

    def get_queryset(self):
        activity = get_object_or_404(Activity, offering=self.offering, slug=self.kwargs['activity_slug'])

        # allow ?hours=n query string to filter age of submissions
        h = self.request.query_params.get('hours', None)
        try:
            hours = datetime.timedelta(hours=float(h))
            cutoff = timezone.now() - hours
        except (ValueError, TypeError):
            cutoff = None

        submission_info = SubmissionInfo.for_activity(activity)
        submission_info.get_all_components()

        # find all of the submitted components we actually care about and build the data we need
        for sub, compdata in submission_info.submissions_and_components():
            if cutoff and sub.created_at < cutoff:
                continue
            for comp, subcomp in compdata:
                if subcomp is None:
                    continue
                if not isinstance(comp, Text.Component):
                    # for now, only send Text submissions
                    continue

                data = {
                    'component': comp.slug,
                    'submitted_at': sub.created_at,
                    'text': subcomp.text,
                    'userid': None,
                    'group': None,
                }
                if submission_info.is_group:
                    data['group'] = sub.group.slug
                else:
                    data['userid'] = sub.member.person.userid

                yield data
