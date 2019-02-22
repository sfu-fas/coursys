from django.core.management.base import BaseCommand
from coredata.tasks import ping, BEAT_TEST_FILE, BEAT_FILE_MAX_AGE
import celery
import os, time

class Command(BaseCommand):
    def handle(self, *args, **options):
        t = ping.apply_async()
        try:
            res = t.get(timeout=30)
        except celery.exceptions.TimeoutError:
            print("Celery task didn't complete: Celery may be down.")
            return

        if res is not True:
            print("Wrong result from celery task")

        # check that the coredata.tasks.beat_test periodic task has run recently
        try:
            beatfile_age = time.time() - os.stat(BEAT_TEST_FILE).st_mtime
            if beatfile_age > BEAT_FILE_MAX_AGE:
                print("Periodic task marker file is old: celery beat likely not processing tasks.")
        except OSError:
            print("Periodic task marker file missing: celery beat likely not processing tasks.")

