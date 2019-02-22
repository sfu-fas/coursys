from courselib.celerytasks import periodic_task
from celery.schedules import crontab
from .models import Reminder, ReminderMessage


@periodic_task(run_every=crontab(minute='0', hour='9'))
def daily_reminders():
    Reminder.create_all_reminder_messages()
    ReminderMessage.send_all()
    ReminderMessage.cleanup()
