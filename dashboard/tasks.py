from celery.task import task
from dashboard.photos import do_photo_fetch

@task(queue='photo')
def fetch_photos_task(emplids):
    return do_photo_fetch(emplids)