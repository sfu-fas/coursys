import json

from django.core.management import BaseCommand

from coredata.models import CourseOffering
from grades.models import NumericActivity
from marking.models import ActivityComponentMark, StudentActivityMark
from marking.views import _DecimalEncoder


class Command(BaseCommand):
    help = """Aggregate marking details from multiple rounds of marking, recovering in cases where marks were imported
    overwriting others.
    Produces importable JSON on stdout."""

    def add_arguments(self, parser):
        parser.add_argument('offering_slug', type=str, help='slug for the offering')
        parser.add_argument('activity_slug', type=str, help='slug the the activity')

    def handle(self, *args, **options):
        offering_slug = options['offering_slug']
        activity_slug = options['activity_slug']
        offering = CourseOffering.objects.get(slug=offering_slug)
        activity = NumericActivity.objects.get(offering=offering, slug=activity_slug)
        if activity.group:
            # haven't handled GroupActivityMark and group lookups below
            raise NotImplementedError()

        act_marks = StudentActivityMark.objects.filter(activity=activity).select_related('numeric_grade__member__person')
        act_mark_lookup = {sam.id: sam for sam in act_marks}
        act_comp_marks = ActivityComponentMark.objects.filter(activity_mark__activity=activity) \
            .select_related('activity_component', 'activity_mark')
        # order by creation, so we get the most-recent after iterating through them.
        act_comp_marks = act_comp_marks.order_by('activity_mark__created_at')

        student_marks = {}
        for acm in act_comp_marks:
            if acm.value is None:
                continue

            am = act_mark_lookup[acm.activity_mark_id]
            userid = am.numeric_grade.member.person.userid
            if userid in student_marks:
                am = student_marks[userid]
            else:
                am = {
                    'userid': userid
                }

            # Keep the overall components from the most recent marks
            am['late_percent'] = acm.activity_mark.late_penalty
            am['mark_penalty'] = acm.activity_mark.mark_adjustment
            am['mark_penalty_reason'] = acm.activity_mark.mark_adjustment_reason
            am['overall_comment'] = acm.activity_mark.overall_comment

            am[acm.activity_component.slug] = {
                'mark': acm.value,
                'comment': acm.comment,
            }

            student_marks[userid] = am

        data = {'combine': False, 'marks': list(student_marks.values())}
        content = json.dumps(data, cls=_DecimalEncoder, indent=2)
        print(content)