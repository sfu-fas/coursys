from celery.task import task, periodic_task
from celery.schedules import crontab

from reports.models import schedule_ping

@periodic_task(run_every=crontab(hour=8, minute=30))
def run_regular_reports():
    schedule_ping()

