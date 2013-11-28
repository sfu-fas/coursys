from celery.task import periodic_task
from celery.task.schedules import crontab
from onlineforms.models import SheetSubmission

@periodic_task(run_every=crontab(hour="8"))
def waiting_forms_reminder():
    SheetSubmission.email_waiting_sheets()
