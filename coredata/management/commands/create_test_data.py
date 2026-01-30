from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        assert settings.DEPLOY_MODE != 'production'
        from coredata.devtest_data_generator import create_all
        create_all()

