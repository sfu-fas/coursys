from django.core.management.base import BaseCommand
from coredata.models import Person


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
    
    def handle(self, *args, **options):
        all_people = Person.objects.all()
        for p in all_people:
            if not p.pref_first_name:
                continue
            if p.first_name == p.pref_first_name:
                continue

            # we're in a true preferred-name case now.
            print(p.name_with_pref())
            p.config['deadname'] = p.first_name
            p.first_name = p.pref_first_name
            p.pref_first_name = None
            if not options['dry_run']:
                p.save()