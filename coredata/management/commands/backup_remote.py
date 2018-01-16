from django.conf import settings
from django.core.management.base import BaseCommand
from optparse import make_option
import pipes, os, subprocess


def backup_commands(db_only=False, method=['incremental']):
    db = ['duplicity'] + method + [
        '--encrypt-key', settings.BACKUP_KEY_ID,
        '--file-prefix', 'db-',
        settings.DB_BACKUP_DIR, settings.BACKUP_REMOTE_URL]
    if db_only:
        return [db]
    submissions = ['duplicity'] + method + [
        '--encrypt-key', settings.BACKUP_KEY_ID,
        '--file-prefix', 'files-',
        settings.SUBMISSION_PATH, settings.BACKUP_REMOTE_URL]
    return [db, submissions] + clean_commands()


def retrieve_commands():
    db = ['duplicity',
          '--encrypt-key', settings.BACKUP_KEY_ID,
          '--file-prefix', 'db-',
          settings.BACKUP_REMOTE_URL, 'restore_destination/db_dump']
    submissions = ['duplicity',
                   '--encrypt-key', settings.BACKUP_KEY_ID,
                   '--file-prefix', 'files-',
                   settings.BACKUP_REMOTE_URL, 'restore_destination/submitted_files']
    return [db, submissions]


def clean_commands():
    db = ['duplicity', 'remove-all-but-n-full', '2', '--file-prefix', 'db-', '--force', settings.BACKUP_REMOTE_URL]
    submissions = ['duplicity',  'remove-all-but-n-full', '1', '--file-prefix', 'files-', '--force', settings.BACKUP_REMOTE_URL]
    return [db, submissions]


def do_check():
    # dry run for admin panel test: simulate './manage.py backup_remote --dry-run --db-only'
    from django.core.management import call_command
    call_command('backup_remote', dry_run=True, db_only=True)


def _run_commands(commands, passphrase=''):
    for cmd in commands:
        res = subprocess.call(cmd, env={'PASSPHRASE': passphrase})
        if res != 0:
            raise RuntimeError('command "%s" exited with %i' % (_shell(cmd), res))


def _shell(cmd):
    return ' '.join(map(pipes.quote, cmd))


class Command(BaseCommand):
    help = 'Send encrypted backup to remote backup server'

    def add_arguments(self, parser):
        parser.add_argument('--backup-commands',
                    dest='backup_commands',
                    action='store_true',
                    default=False,
                    help="Output duplicity commands to do a backup")
        parser.add_argument('--restore-commands',
                    dest='retrieve_commands',
                    action='store_true',
                    default=False,
                    help="Output duplicity commands to retrieve backups")
        parser.add_argument('--cleanup-commands',
                    dest='cleanup_commands',
                    action='store_true',
                    default=False,
                    help="Output duplicity commands to purge old full backups")
        parser.add_argument('--also-files',
                    dest='also_files',
                    action='store_true',
                    default=False,
                    help='Backup the stored files as well as the database snapshots [default: database only]')
        parser.add_argument('--full',
                    dest='full',
                    action='store_true',
                    default=False,
                    help="Do a full backup (as opposed to incremental)")
        parser.add_argument('--dry-run', '-n',
                    dest='dry_run',
                    action='store_true',
                    default=False,
                    help='Do a dry run of the duplicity backup.')

    def handle(self, *args, **options):
        passphrase = settings.BACKUP_KEY_PASSPHRASE
        full = options['full']
        dry_run = options['dry_run']
        method = ['full'] if full else ['--full-if-older-than', '1M']
        if dry_run:
            method += ['--dry-run']

        if options['backup_commands']:
            # duplicity commands to create a backup
            for cmd in backup_commands(method=method):
                print(('PASSPHRASE=%s ' % (pipes.quote(passphrase)) + _shell(cmd)))
            return

        if options['retrieve_commands']:
            # duplicity commands to retrieve the backup files
            for cmd in retrieve_commands():
                print(('PASSPHRASE=%s ' % (pipes.quote(passphrase)) + _shell(cmd)))
            return

        if options['cleanup_commands']:
            # duplicity commands to clean out old full backups
            for cmd in clean_commands():
                print((' '.join(map(pipes.quote, cmd))))
            return

        # do the backup
        _run_commands(backup_commands(method=method, db_only=not options['also_files']), passphrase=passphrase)

        if method == 'full':
            _run_commands(clean_commands())
