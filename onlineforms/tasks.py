from courselib.celerytasks import task
from django.conf import settings
from onlineforms.models import SheetSubmission


@task()
def waiting_forms_reminder():
    if not settings.DO_IMPORTING_HERE:
        return
    SheetSubmission.email_waiting_sheets()

@task()
def reject_dormant_initial():
    SheetSubmission.reject_dormant_initial()
