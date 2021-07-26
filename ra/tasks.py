from courselib.celerytasks import periodic_task
from celery.schedules import crontab
from ra.models import RAAppointment, RARequest


@periodic_task(run_every=crontab(minute='0', hour='13'))
def expiring_ras_reminder():
    RAAppointment.email_expiring_ras()
    RARequest.email_expiring_ras()
