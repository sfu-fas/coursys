from courselib.celerytasks import task
from django.conf import settings
from ra.models import RAAppointment, RARequest


@task()
def expiring_ras_reminder():
    if not settings.DO_IMPORTING_HERE:
        return
    RAAppointment.email_expiring_ras()
    RARequest.email_expiring_ras()
