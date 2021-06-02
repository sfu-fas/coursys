import datetime
import random

from django.core.management.base import BaseCommand
from django.conf import settings

from coredata.models import CourseOffering, Member
from courselib.testing import TEST_COURSE_SLUG
from discipline.models import DisciplineCaseInstrStudent, DisciplineCaseInstrNonStudent, DisciplineGroup


class Command(BaseCommand):
    help = 'Build some test data for development.'

    def add_arguments(self, parser):
        parser.add_argument('--cases', type=int, default=50)

    def handle(self, *args, **options):
        assert not settings.DO_IMPORTING_HERE
        assert settings.DEPLOY_MODE != 'production'

        o = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        instr = Member.objects.filter(offering=o, role='INST')[0].person
        students = [m.person for m in Member.objects.filter(offering=o, role='STUD')]

        group = DisciplineGroup(name='Group ' + str(random.randint(1,10000)), offering=o)
        group.save()

        for i in range(options['cases']):
            if random.choice(['student', 'student', 'student', 'nonstudent']) == 'nonstudent':
                c = DisciplineCaseInstrNonStudent(owner=instr, offering=o, emplid=0, userid='fakeuser', email='fake@example.com', last_name='Lname', first_name='Fname')
            else:
                p = random.choice(students)
                c = DisciplineCaseInstrStudent(owner=instr, offering=o, student=p)

            c.group = random.choice([None, group])

            if random.choice(['completed', 'incomplete']) == 'completed':
                c.contact_email_text = 'Did you?'
                c.contacted = 'MAIL'
                c.contact_date = datetime.date.today()
                c.response = random.choice(['DECL', 'MAIL', 'MET'])
                c.meeting_date = datetime.date.today()
                c.meeting_summary = 'Talking happened.'
                c.facts = 'They probably did it.'
                c.penalty = random.choice(['MARK', 'ZERO', 'REDO', 'NONE'])
                c.refer = random.choice([True, False])
                c.letter_review = True
                c.letter_sent = 'MAIL'
                c.letter_date = datetime.date.today()
                c.letter_text = 'Officially, yes.'
                c.penalty_implemented = random.choice([True, False])

            c.save()


