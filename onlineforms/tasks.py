from celery.task import periodic_task
from celery.schedules import crontab
from onlineforms.models import SheetSubmission

@periodic_task(run_every=crontab(day_of_week='1,3,5', hour="8", minute="0"))
def waiting_forms_reminder():
    SheetSubmission.sheet_maintenance()
