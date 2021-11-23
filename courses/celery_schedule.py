from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'beat_test': {
        'task': 'coredata.tasks.beat_test',
        'schedule': crontab(minute='*/5', hour='*'),
    },
    'regular_backup': {
        'task': 'coredata.tasks.regular_backup',
        'schedule': crontab(minute=0, hour='*/3'),
    },
    'daily_import': {
        'task': 'coredata.tasks.daily_import',
        'schedule': crontab(minute='30', hour='8'),
    },
    'check_sims_connection': {
        'task': 'coredata.tasks.check_sims_connection',
        'schedule': crontab(minute=0, hour='*/3'),
    },
    'haystack_rebuild': {
        'task': 'coredata.tasks.haystack_rebuild',
        'schedule': crontab(minute='0', hour='2', day_of_week='saturday'),
    },
    'expiring_roles': {
        'task': 'coredata.tasks.expiring_roles',
        'schedule': crontab(minute='30', hour='7', day_of_week='mon,thu'),
    },
    'photo_password_update_task': {
        'task': 'dashboard.tasks.photo_password_update_task',
        'schedule': crontab(day_of_month="10,20,30", hour=2, minute=0),
    },

    'program_info_for_advisorvisits': {
        'task': 'advisornotes.tasks.program_info_for_advisorvisits',
        'schedule': crontab(minute=0, hour='2'),
    },
    'send_digests': {
        'task': 'forum.tasks.send_digests',
        'schedule': crontab(hour='*', minute='0'),
    },
    'update_statuses_to_current': {
        'task': 'grad.tasks.update_statuses_to_current',
        'schedule': crontab(minute=0, hour=3),
    },
    'waiting_forms_reminder': {
        'task': 'onlineforms.tasks.waiting_forms_reminder',
        'schedule': crontab(day_of_week='1,3,5', hour="13", minute="0"),
    },
    'expiring_ras_reminder': {
        'task': 'ta.tasks.expiring_ras_reminder',
        'schedule': crontab(minute='0', hour='13'),
    },
    'daily_reminders': {
        'task': 'reminders.tasks.daily_reminders',
        'schedule': crontab(minute='0', hour='9'),
    },
    'run_regular_reports': {
        'task': 'reports.tasks.run_regular_reports',
        'schedule': crontab(hour=9, minute=15),
    },
}