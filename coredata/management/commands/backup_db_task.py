import sys

from django.core.management.base import BaseCommand
from coredata.tasks import backup_database

class Command(BaseCommand):
    help = "Trigger database backup task (and wait for completion)."

    def handle(self, *args, **options):
        sys.stdout.write("Starting database backup task... ")
        res = backup_database.delay()
        res.get()
        sys.stdout.write("Backup complete.\n")
