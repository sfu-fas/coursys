from django.conf import settings
from courselib.celerytasks import task, periodic_task
from celery.schedules import crontab
from dashboard.photos import do_photo_fetch, change_photo_password

@task(queue='photo')
def fetch_photos_task(emplids):
    return do_photo_fetch(emplids)

if not settings.USE_CELERY:
    # no celery? Disable.
    fetch_photos_task.delay = lambda emplids: None

@periodic_task(run_every=crontab(day_of_month="10,20,30", hour=2, minute=0))
def photo_password_update_task():
    if settings.DO_IMPORTING_HERE:
        change_photo_password()
