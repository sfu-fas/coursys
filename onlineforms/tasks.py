from courselib.celerytasks import task
from celery.schedules import crontab
from onlineforms.models import SheetSubmission


@task()
def waiting_forms_reminder():
    SheetSubmission.sheet_maintenance()
