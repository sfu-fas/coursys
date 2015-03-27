from django.core.management.base import BaseCommand
from grad.importer import import_grads
from optparse import make_option

class Command(BaseCommand):
    args = '<emplids>'
    help = 'Import data from SIMS into our system for all grad students (or just the given EMPLIDs)'

    option_list = BaseCommand.option_list + (
        make_option('--dry-run', '-n',
            dest='dryrun',
            action='store_true',
            default=False,
            help="Don't actually write changes"),
        )

    def handle(self, *args, **options):
        import_grads(dry_run=options['dryrun'], verbosity=int(options['verbosity']), import_emplids=args)
