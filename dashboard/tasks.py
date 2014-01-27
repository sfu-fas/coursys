from coredata.celery import flexible_task
from django.core.cache import cache

@flexible_task(queue='fast')
def fetch_photos(emplids):
    print emplids


