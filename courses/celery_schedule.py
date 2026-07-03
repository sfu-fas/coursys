from celery.schedules import crontab


def beat(task: str, schedule: int | crontab, *, queue: str = 'batch'):
    """
    Helper to create a key/value pair for the celerybeat schedule.
    """
    entry = {
        'task': task,
        'schedule': schedule,
        'queue': queue,
        'options': { 'queue': queue, 'routing_key': queue },
    }
    return (task, entry)


CELERY_BEAT_SCHEDULE = dict([
    beat('coredata.tasks.beat_test', 300, queue='fast'),
    beat('coredata.tasks.backup_database', crontab(minute=0, hour='*/3'), queue='batch'),
    beat('coredata.tasks.csrpt_refresh_periodic', 7200, queue='sims'),
    beat('coredata.tasks.daily_import', crontab(minute='30', hour='8'), queue='sims'),
    beat('grad.tasks.grad_daily_import', crontab(minute='40', hour='8'), queue='sims'),
    beat('coredata.tasks.check_sims_connection', crontab(minute=0, hour='*/3'), queue='sims'),
    beat('coredata.tasks.expire_sessions_conveniently', crontab(minute='0', hour='4')),
    beat('coredata.tasks.haystack_rebuild', crontab(minute='0', hour='2', day_of_week='saturday')),
    beat('coredata.tasks.expiring_roles', crontab(minute='30', hour='7', day_of_week='mon,thu')),
    beat('dashboard.tasks.photo_password_update_task', crontab(day_of_month="10,20,30", hour=2, minute=0)),
    beat('advisornotes.tasks.cleanup_advising_surveys', crontab(minute=0, hour='2')),
    beat('advisornotes.tasks.program_info_for_advisorvisits', crontab(minute=5, hour='2')),
    beat('forum.tasks.send_digests', crontab(hour='*', minute='0')),
    beat('grad.tasks.update_statuses_to_current', crontab(minute=0, hour=3)),
    beat('onlineforms.tasks.waiting_forms_reminder', crontab(day_of_week="1", hour="13", minute="0")),
    beat('onlineforms.tasks.reject_dormant_initial', crontab(hour="18", minute="0")),
    beat('ra.tasks.expiring_ras_reminder', crontab(minute='0', hour='13')),
    beat('reminders.tasks.daily_reminders', crontab(minute='0', hour='9')),
    beat('reports.tasks.run_regular_reports', crontab(hour=9, minute=15)),
    beat('ta.tasks.check_and_execute_reminders', crontab(minute='0', hour='8')),
    beat('log.tasks.log_regular', crontab(hour='*', minute='0,15,30,45'), queue='fast'),
    beat('log.tasks.log_avg_request_duration', crontab(hour='*', minute=0), queue='fast'),
])
