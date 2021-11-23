from django.conf import settings
from courselib.celerytasks import task
from dashboard.photos import do_photo_fetch, change_photo_password

@task(queue='photo')
def fetch_photos_task(emplids):
    return do_photo_fetch(emplids)

if not settings.USE_CELERY:
    # no celery? Disable.
    fetch_photos_task.delay = lambda emplids: None

@task()
def photo_password_update_task():
    if settings.DO_IMPORTING_HERE:
        change_photo_password()
