from django.core.management.base import BaseCommand
from coredata.devtest_data_generator import create_all


class Command(BaseCommand):
    def handle(self, *args, **options):
        create_all()
