import itertools
import string
import random

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core import serializers
from django.db import transaction

from coredata.models import CourseOffering, Member, Person


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
        assert not Person.objects.all().exists(), 'Must start from a clean database (after migration).'

        with transaction.atomic():
            for obj in serializers.deserialize('json', open(options['data_file'], 'rt', encoding='utf8').read()):
                obj.save()

        with transaction.atomic():
            n_fake = 200
            fake_students = [Person(
                emplid=str(500000000 + i),
                userid='fake%03i' % (i,),
                last_name='Fake',
                first_name=random_name(8),
                middle_name=random_name(5),
                title=random.choice(['Mr', 'M', 'Ms', 'Dr', 'Count'])
            ) for i in range(n_fake)]
            for p in fake_students:
                p.pref_first_name = random.choice([None, p.first_name[:4]])
                p.save()

            students_per_class = 10
            for o in CourseOffering.objects.all():
                student_people = random.choices(fake_students, k=students_per_class)
                for p in student_people:
                    m = Member(person=p, offering=o, role='STUD', added_reason='AUTO', credits=3, career='UGRD')
                    m.save()
