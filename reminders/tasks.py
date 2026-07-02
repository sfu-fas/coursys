from courselib.celerytasks import task
from django.conf import settings
from .models import Reminder, ReminderMessage


@task()
def daily_reminders():
    if not settings.DO_IMPORTING_HERE:
        return
    Reminder.create_all_reminder_messages()
    ReminderMessage.send_all()
    ReminderMessage.cleanup()
