from courselib.celerytasks import task
from celery.schedules import crontab
from ra.models import RAAppointment, RARequest


@task()
def expiring_ras_reminder():
    RAAppointment.email_expiring_ras()
    RARequest.email_expiring_ras()
