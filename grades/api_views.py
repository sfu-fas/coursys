from rest_framework import generics

from coredata.models import Member
from grades.models import all_activities_filter
from grades.serializers import ActivitySerializer, GradeMarkSerializer, StatsSerializer, StudentSerializer
from courselib.rest import APIConsumerPermissions, IsOfferingMember, IsOfferingStaff, CacheMixin


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


class OfferingStudents(CacheMixin, generics.ListAPIView):
    """
    List of students in the course.

    User must be an instructor or TA of the course.
    """
    serializer_class = StudentSerializer

    permission_classes = (APIConsumerPermissions, IsOfferingStaff,)
    consumer_permissions = set(['courses', 'instr-info'])
    cache_hours = 2

    def get_queryset(self):
        return [m.person for m in Member.objects.filter(offering=self.offering, role='STUD').select_related('person')]

