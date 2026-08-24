from django.core.management.base import BaseCommand
from coredata.tasks import our_update_index


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--full-rebuild', action='store_true', default=False)
    
    def handle(self, *args, **options):
        update_only = not options['full_rebuild']
        our_update_index.delay(update_only=update_only)
        print(f"Started our_update_index(update_only={update_only})")