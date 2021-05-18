import datetime
import string
import random

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core import serializers
from django.db import transaction

from coredata.models import CourseOffering, Member, Person, Role, Unit


n_fake_students = 200
n_fake_grads = 20
students_per_class = 10


def random_name(l):
    """
    Generate a random not-very-name-like string.
    """
    n = random.choice(string.ascii_uppercase)
    for _ in range(l-1):
        n = n + random.choice(string.ascii_lowercase + 'àêïõú')
    return n


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('data_file', type=str)

    def handle(self, *args, **options):
        assert settings.DEPLOY_MODE != 'production'

        # import public data dumped from production
        with transaction.atomic():
            for obj in serializers.deserialize('json', open(options['data_file'], 'rt', encoding='utf8').read()):
                obj.save()

        # create fake students and a TA in every offering
        with transaction.atomic():
            fake_students = [Person(
                emplid=str(500000000 + i),
                userid='fake%03i' % (i,),
                last_name='Fake',
                first_name=random_name(8),
                middle_name=random_name(5),
                title=random.choice(['Mr', 'M', 'Ms', 'Dr'])
            ) for i in range(n_fake_students)]
            for p in fake_students:
                p.pref_first_name = random.choice([None, p.first_name[:4]])
                p.save()

            fake_grads = [Person(
                emplid=str(510000000 + i),
                userid='grad%03i' % (i,),
                last_name='Grad',
                first_name=random_name(8),
                middle_name=random_name(5),
                title=random.choice(['Mr', 'M', 'Ms', 'Dr'])
            ) for i in range(n_fake_grads)]
            for p in fake_grads:
                p.pref_first_name = random.choice([None, p.first_name[:4]])
                p.save()

            for o in CourseOffering.objects.all():
                ta_person = random.choice(fake_grads)
                m = Member(person=ta_person, offering=o, role='TA', added_reason='AUTO', credits=0, career='NONS')
                m.save()
                student_people = set(random.choices(fake_students, k=students_per_class))
                for p in student_people:
                    m = Member(person=p, offering=o, role='STUD', added_reason='AUTO', credits=3, career='UGRD')
                    m.save()

            r = Role(person=Person.objects.get(userid='ggbaker'), role='SYSA', unit=Unit.objects.get(label='UNIV'), expiry=datetime.date.today() + datetime.timedelta(days=730))
            r.save()

