from django.conf import settings
from django.core.management.base import BaseCommand
from optparse import make_option
import datetime, os, glob


class Command(BaseCommand):
    help = 'Create a database dump'

    def add_arguments(self, parser):
        parser.add_argument('--clean-old',
            dest='clean_old',
            action='store_true',
            default=False,
            help="Clean old dumps as well?")
        parser.add_argument('--fast',
            action='store_true',
            default=False,
            help="Produce the fast mysqldump, not the line-by-line diffable dump.")


    def handle(self, *args, **options):
        from dbdump.management.commands import dbdump
        path = settings.DB_BACKUP_DIR
        filename_format = '%Y-%m-%dT%H-%M-%S.dump'

        now = datetime.datetime.now().replace(microsecond=0)
        filename = now.strftime(filename_format)

        if 'ssl' in settings.DATABASES['default']['OPTIONS']:
            sslarg = ' --ssl-ca=' + settings.DATABASES['default']['OPTIONS']['ssl']['ca']
        else:
            sslarg = ''

        if options['fast']:
            format_args = ''
        else:
            format_args = '--single-transaction --skip-extended-insert'
        dbdump.Command().handle(backup_directory=path, filename=filename, compression_command='gzip',
                                raw_args=format_args + sslarg)

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
                if dt < now - datetime.timedelta(days=30):
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
