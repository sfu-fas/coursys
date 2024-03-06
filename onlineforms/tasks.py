from courselib.celerytasks import task
from celery.schedules import crontab
from onlineforms.models import SheetSubmission


@task()
def waiting_forms_reminder():
    SheetSubmission.email_waiting_sheets()

@task()
def reject_dormant_initial():
    SheetSubmission.reject_dormant_initial()
