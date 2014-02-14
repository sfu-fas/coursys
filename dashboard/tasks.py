from celery.task import task
from dashboard.photos import do_photo_fetch, change_photo_password

@task(queue='photo')
def fetch_photos_task(emplids):
    return do_photo_fetch(emplids)

#@periodic_task(run_every=crontab(day_of_month="10,20,30", hour=8, minute=0))
#def photo_password_update_task():
#    change_photo_password()
