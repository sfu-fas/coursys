from django.core.management.base import BaseCommand
from grad.importer import rogue_grad_finder
from optparse import make_option

class Command(BaseCommand):
    args = '<unit_slug>'
    help = 'Examine rogue GradStudent objects for this unit'

    option_list = BaseCommand.option_list + (
        make_option('--dry-run', '-n',
            dest='dryrun',
            action='store_true',
            default=False,
            help="Don't actually write changes"),
        )

    def handle(self, *args, **options):
        rogue_grad_finder(args[0], dry_run=options['dryrun'], verbosity=int(options['verbosity']))
