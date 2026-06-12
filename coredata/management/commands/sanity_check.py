import time
from django.core.management.base import BaseCommand
from django.core.cache import cache

from coredata import panel

class Command(BaseCommand):
    help = 'Check that must pass before we allow the server to start.'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options):
        _, failed = panel.sanity_checks()
        if failed:
            time.sleep(2)  # rate-limit container restarts a little
            raise RuntimeError(str(failed))

