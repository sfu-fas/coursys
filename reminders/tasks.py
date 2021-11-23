from courselib.celerytasks import task
from celery.schedules import crontab
from .models import Reminder, ReminderMessage


@task()
def daily_reminders():
    Reminder.create_all_reminder_messages()
    ReminderMessage.send_all()
    ReminderMessage.cleanup()
