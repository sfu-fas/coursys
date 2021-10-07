"""
Create quiz TimeSpecialCase for all students in a particular lab/tutorial section.

Usage will be like:
./manage.py special_case_tutorial 2020su-cmpt-120-d1 q1 D101 '2021-10-07T09:30' '2021-10-07T10:30'
"""

import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from iso8601 import iso8601

from coredata.models import CourseOffering, Member
from quizzes.models import Quiz, TimeSpecialCase


def parse_datetime(s: str) -> datetime.datetime:
    return iso8601.parse_date(s).replace(tzinfo=None)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('offering_slug', type=str, help='CourseOffering slug')
        parser.add_argument('activity_slug', type=str, help='the slug of the Activity with the quiz')
        parser.add_argument('section', type=str, help='lab/tutorial section to modify')
        parser.add_argument('start_time', type=parse_datetime, help='start time for this section')
        parser.add_argument('end_time', type=parse_datetime, help='end time for this section')

    def handle(self, *args, **options):
        offering_slug = options['offering_slug']
        activity_slug = options['activity_slug']
        section = options['section']
        start_time = options['start_time']
        end_time = options['end_time']

        offering = CourseOffering.objects.get(slug=offering_slug)
        quiz = Quiz.objects.get(activity__slug=activity_slug, activity__offering=offering)
        members = Member.objects.filter(offering=offering, role='STUD', labtut_section=section)

        with transaction.atomic():
            for m in members:
                TimeSpecialCase.objects.update_or_create(
                    quiz=quiz, student=m,
                    defaults={'start': start_time, 'end': end_time}
                )


