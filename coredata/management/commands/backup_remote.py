from django.conf import settings
from django.core.management.base import BaseCommand
from optparse import make_option
import pipes, os, subprocess

def ssh_dest():
    return '%s@%s' % (settings.BACKUP_USER, settings.BACKUP_SERVER)

def duplicity_remote(subdir):
    return 'scp://%s/%s' % (ssh_dest(), os.path.join(settings.BACKUP_PATH, subdir))

def backup_commands(method='incremental'):
    db = ['duplicity', method, settings.DB_BACKUP_DIR, duplicity_remote('db_dump')]
    submissions = ['duplicity', method, settings.SUBMISSION_PATH, duplicity_remote('submitted_files')]
    return [db, submissions]

def retrieve_commands():
    db = ['duplicity', duplicity_remote('db_dump'), 'restore_destination/db_dump']
    submissions = ['duplicity', duplicity_remote('submitted_files'), 'restore_destination/submitted_files']
    return [db, submissions]

def clean_commands():
    db = ['duplicity', 'remove-all-but-n-full', '2', '--force', duplicity_remote('db_dump')]
    submissions = ['duplicity',  'remove-all-but-n-full', '1', '--force', duplicity_remote('submitted_files')]
    return [db, submissions]

def do_checks():
    # dry run for admin panel test
    passphrase = settings.BACKUP_PASSPHRASE
    for cmd in backup_commands('--dry-run'):
        subprocess.call(cmd, env={'PASSPHRASE': passphrase})


class Command(BaseCommand):
    help = 'Send encrypted backup to remote backup server'

    option_list = BaseCommand.option_list + (
        make_option('--ssh-command',
                    dest='ssh-command',
                    action='store_true',
                    default=False,
                    help="Output ssh command to get to backup server"),
        make_option('--backup-commands',
                    dest='backup-commands',
                    action='store_true',
                    default=False,
                    help="Output duplicity commands to do a backup"),
        make_option('--retrieve-commands',
                    dest='retrieve-commands',
                    action='store_true',
                    default=False,
                    help="Output duplicity commands to retrieve backups"),
        make_option('--cleanup-commands',
                    dest='cleanup-commands',
                    action='store_true',
                    default=False,
                    help="Output duplicity commands to purge old full backups"),

        make_option('--full',
                    dest='full',
                    action='store_true',
                    default=False,
                    help="Do a full backup (as opposed to incremental)"),
    )

    def handle(self, *args, **options):
        passphrase = settings.BACKUP_PASSPHRASE
        method = 'incremental'
        if options['full']:
            method = 'full'

        if options['ssh-command']:
            # command to SSH to the backup server, for testing
            print 'ssh ' + pipes.quote(ssh_dest())
            return

        if options['backup-commands']:
            # duplicity commands to create an incremental backup
            for cmd in backup_commands(method=method):
                print 'PASSPHRASE=%s ' % (pipes.quote(passphrase)) + ' '.join(map(pipes.quote, cmd))
            return

        if options['retrieve-commands']:
            # duplicity commands to retrieve the backup files
            for cmd in retrieve_commands():
                print 'PASSPHRASE=%s ' % (pipes.quote(passphrase)) + ' '.join(map(pipes.quote, cmd))
            return

        if options['cleanup-commands']:
            # duplicity commands to clean out old full backups
            for cmd in clean_commands():
                print ' '.join(map(pipes.quote, cmd))
            return

        # actually do the backup
        for cmd in backup_commands(method=method):
            subprocess.call(cmd, env={'PASSPHRASE': passphrase})

        if options['full']:
            for cmd in clean_commands(method=method):
                subprocess.call(cmd)
