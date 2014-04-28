from django.conf import settings
from django.core.management.base import BaseCommand
from optparse import make_option
import datetime, os, glob


class Command(BaseCommand):
    help = 'Create a database dump'

    option_list = BaseCommand.option_list + (
        make_option('--clean-old',
            dest='clean_old',
            action='store_true',
            default=False,
            help="Clean old dumps as well?"),
    )

    def handle(self, *args, **options):
        from dbdump.management.commands import dbdump
        path = settings.DB_BACKUP_DIR
        filename_format = '%Y-%m-%dT%H-%M-%S.dump'

        now = datetime.datetime.now().replace(microsecond=0)
        filename = now.strftime(filename_format)

        dbdump.Command().handle(backup_directory=path, filename=filename, compression_command='gzip')

        if options['clean_old']:
            dates_covered = set()
            dumps = glob.glob(os.path.join(path, '*.dump.gz'))
            dumps.sort()
            for fullpath in dumps:
                fn = os.path.basename(fullpath)
                if fn.endswith('.gz'):
                    fn = fn[:-3]

                try:
                    dt = datetime.datetime.strptime(fn, filename_format)
                except ValueError:
                    # doesn't match filename format: ignore.
                    continue

                remove = False
                if dt < now - datetime.timedelta(days=14):
                    # remove all dumps older than two weeks
                    remove = True
                elif dt < now - datetime.timedelta(days=2):
                    # two days and older: keep one-per-day
                    date = dt.date()
                    if date in dates_covered:
                        remove = True
                    else:
                        dates_covered.add(date)

                if remove:
                    os.remove(fullpath)
