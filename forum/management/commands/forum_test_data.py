from django.core.management.base import BaseCommand
from django.conf import settings

from coredata.models import CourseOffering
from courselib.testing import TEST_COURSE_SLUG
from forum.models import Forum


class Command(BaseCommand):
    help = 'Build some test data for development.'

    def handle(self, *args, **options):
        assert not settings.DO_IMPORTING_HERE
        assert settings.DEPLOY_MODE != 'production'

        offering = CourseOffering.objects.get(slug=TEST_COURSE_SLUG)
        f = Forum(offering=offering)
        f.enabled = True
        f.identity = 'INST'
        f.save()

