from django.core.management.base import BaseCommand
from coredata.tasks import ping, beat_time_okay
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
        if not beat_time_okay():
            print("Periodic task marker file is old: celery beat likely not processing tasks.")
