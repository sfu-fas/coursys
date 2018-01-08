from django.conf import settings
from django.core.management.base import BaseCommand
from optparse import make_option
import pipes, os, subprocess


def ssh_dest():
    return '%s@%s' % (settings.BACKUP_USER, settings.BACKUP_SERVER)


def duplicity_remote(subdir):
    return 'scp://%s/%s' % (ssh_dest(), os.path.join(settings.BACKUP_PATH, subdir))


def backup_commands(db_only=False, method=['incremental']):
    db = ['duplicity'] + method + [settings.DB_BACKUP_DIR, duplicity_remote('db_dump')]
    if db_only:
        return [db]
    submissions = ['duplicity'] + method + [settings.SUBMISSION_PATH, duplicity_remote('submitted_files')]
    return [db, submissions]


def retrieve_commands():
    db = ['duplicity', duplicity_remote('db_dump'), 'restore_destination/db_dump']
    submissions = ['duplicity', duplicity_remote('submitted_files'), 'restore_destination/submitted_files']
    return [db, submissions]


def clean_commands():
    db = ['duplicity', 'remove-all-but-n-full', '2', '--force', duplicity_remote('db_dump')]
    submissions = ['duplicity',  'remove-all-but-n-full', '1', '--force', duplicity_remote('submitted_files')]
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
        parser.add_argument('--ssh-command',
                    dest='ssh_command',
                    action='store_true',
                    default=False,
                    help="Output ssh command to get to backup server")
        parser.add_argument('--backup-commands',
                    dest='backup_commands',
                    action='store_true',
                    default=False,
                    help="Output duplicity commands to do a backup")
        parser.add_argument('--retrieve-commands',
                    dest='retrieve_commands',
                    action='store_true',
                    default=False,
                    help="Output duplicity commands to retrieve backups")
        parser.add_argument('--cleanup-commands',
                    dest='cleanup_commands',
                    action='store_true',
                    default=False,
                    help="Output duplicity commands to purge old full backups")
        parser.add_argument('--db-only',
                    dest='db_only',
                    action='store_true',
                    default=False,
                    help='Backup the database only [default: database and submitted files]')
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
        passphrase = settings.BACKUP_PASSPHRASE
        full = options['full']
        dry_run = options['dry_run']
        method = ['full' if full else 'incremental']
        if dry_run:
            method += ['--dry-run']

        if options['ssh_command']:
            # command to SSH to the backup server, for testing
            print((_shell(['ssh', ssh_dest()])))
            return

        if options['backup_commands']:
            # duplicity commands to create an incremental backup
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
        _run_commands(backup_commands(method=method, db_only=options['db_only']), passphrase=settings.BACKUP_PASSPHRASE)

        if method == 'full':
            _run_commands(clean_commands())
