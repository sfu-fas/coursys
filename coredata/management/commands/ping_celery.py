from django.core.management.base import BaseCommand
from coredata.tasks import ping
import celery
class Command(BaseCommand):
    def handle(self, *args, **options):
        t = ping.apply_async()
        try:
            res = t.get(timeout=10)
        except celery.exceptions.TimeoutError:
            print "Celery task didn't complete: Celery may be down."
            return

        if res is not True:
            print "Wrong result from celery task"