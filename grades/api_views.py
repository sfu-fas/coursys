from rest_framework import generics

from grades.models import all_activities_filter
from grades.serializers import ActivitySerializer, GradeMarkSerializer, StatsSerializer
from courselib.rest import APIConsumerPermissions, IsOfferingMember, CacheMixin


class _ActivityInfoView(CacheMixin, generics.ListAPIView):
    """
    Abstract view for returning info on each activity in the offering
    """
    permission_classes = (APIConsumerPermissions, IsOfferingMember,)
    consumer_permissions = set(['courses'])
    cache_hours = 2

    def get_queryset(self):
        activities = all_activities_filter(self.offering)
        if self.member.role == 'STUD':
            activities = [a for a in activities if a.status in ['RLS', 'URLS']]
        return activities


class OfferingActivities(_ActivityInfoView):
    """
    List of all activities in this course offering, with details.

    User must be a student/staff in the course.
    """
    serializer_class = ActivitySerializer


class OfferingGrades(_ActivityInfoView):
    """
    List of this student's grades in each activity, if they are available/visible.

    User must be a student in the course.
    """
    serializer_class = GradeMarkSerializer


class OfferingStats(_ActivityInfoView):
    """
    Summary statistics for each activity.

    User must be a student in the course.
    """
    serializer_class = StatsSerializer
