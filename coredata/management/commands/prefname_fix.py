from django.core.management.base import BaseCommand
from coredata.models import Person
from django.db.models.expressions import F


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
    
    def handle(self, *args, **options):
        all_people = Person.objects.exclude(pref_first_name=F('first_name')).order_by('last_name', 'pref_first_name')
        for p in all_people:
            if p.first_name == p.pref_first_name: # should be excluded by the query, but just in case
                # already have no separate preferred name: that's the goal
                continue
            if p.pref_first_name is None:
                continue

            # we're in a true preferred-name case now.
            print(p.sortname_pref_only())
            p.config['legal_first_name_do_not_use'] = p.first_name
            p.first_name = p.pref_first_name

            # a few users have our manually-set pref_first_name: remove if appropriate
            if 'pref_first_name' in p.config and p.config['pref_first_name'] == p.pref_first_name:
                del p.config['pref_first_name']

            if not options['dry_run']:
                p.save()