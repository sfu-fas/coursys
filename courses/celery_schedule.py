from celery.schedules import crontab


def beat(task: str, schedule: int | crontab, *, queue: str = 'batch'):
    """
    Helper to create a key/value pair for the celerybeat schedule.
    """
    entry = {
        'task': task,
        'schedule': schedule,
        'options': { 'queue': queue, 'routing_key': queue },
    }
    return (task, entry)


# Celerybeat has had consistent problems with non-UTC timezone. Thus it has been told to schedule in
# UTC, and all times here must be in UTC (i.e. Vancouver + 7 hours)
def h(hour):
    "Convert hour from Vancouver to UTF"
    return (hour + 7) % 24


CELERY_BEAT_SCHEDULE = dict([
    beat('coredata.tasks.beat_test', 300, queue='fast'),
    beat('coredata.tasks.backup_database', crontab(minute=0, hour='*/3'), queue='batch'),
    beat('coredata.tasks.csrpt_refresh_periodic', 7200, queue='sims'),
    beat('coredata.tasks.daily_import', crontab(minute='30', hour=h(8)), queue='sims'),
    beat('grad.tasks.grad_daily_import', crontab(minute='40', hour=h(8)), queue='sims'),
    beat('coredata.tasks.check_sims_connection', crontab(minute=0, hour='*/3'), queue='sims'),
    beat('coredata.tasks.expire_sessions_conveniently', crontab(minute='0', hour=h(4))),
    beat('coredata.tasks.haystack_rebuild', crontab(minute='0', hour=h(2), day_of_week='saturday')),
    beat('coredata.tasks.expiring_roles', crontab(minute='30', hour=h(7), day_of_week='mon,thu')),
    beat('dashboard.tasks.photo_password_update_task', crontab(day_of_month="10,20,30", hour=h(2), minute=0)),
    beat('advisornotes.tasks.cleanup_advising_surveys', crontab(minute=0, hour=h(2))),
    beat('advisornotes.tasks.program_info_for_advisorvisits', crontab(minute=5, hour=h(2))),
    beat('forum.tasks.send_digests', crontab(hour='*', minute='0')),
    beat('grad.tasks.update_statuses_to_current', crontab(minute=0, hour=h(3))),
    beat('onlineforms.tasks.waiting_forms_reminder', crontab(day_of_week="1", hour=h(13), minute="0")),
    beat('onlineforms.tasks.reject_dormant_initial', crontab(hour=h(18), minute="0")),
    beat('ra.tasks.expiring_ras_reminder', crontab(minute='0', hour=h(13))),
    beat('reminders.tasks.daily_reminders', crontab(minute='0', hour=h(9))),
    beat('reports.tasks.run_regular_reports', crontab(hour=h(9), minute=15), queue='sims'),
    beat('ta.tasks.check_and_execute_reminders', crontab(minute='0', hour=h(8))),
    beat('log.tasks.log_regular', crontab(hour='*', minute='0,15,30,45'), queue='fast'),
    beat('log.tasks.log_avg_request_duration', crontab(hour='*', minute=0), queue='fast'),
])
