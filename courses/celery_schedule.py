from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'coredata.tasks.beat_test': {
        'task': 'coredata.tasks.beat_test',
        'schedule': crontab(minute='*/5', hour='*'),
    },
    'coredata.tasks.regular_backup': {
        'task': 'coredata.tasks.regular_backup',
        'schedule': crontab(minute=0, hour='*/3'),
    },
    'coredata.tasks.daily_import': {
        'task': 'coredata.tasks.daily_import',
        'schedule': crontab(minute='30', hour='8'),
    },
    'grad.tasks.grad_daily_import': {
        'task': 'grad.tasks.grad_daily_import',
        'schedule': crontab(minute='40', hour='8'),
    },
    'coredata.tasks.check_sims_connection': {
        'task': 'coredata.tasks.check_sims_connection',
        'schedule': crontab(minute=0, hour='*/3'),
    },
    'coredata.tasks.expire_sessions_conveniently': {
        'task': 'coredata.tasks.expire_sessions_conveniently',
        'schedule': crontab(minute='0', hour='4'),
    },
    'coredata.tasks.haystack_rebuild': {
        'task': 'coredata.tasks.haystack_rebuild',
        'schedule': crontab(minute='0', hour='2', day_of_week='saturday'),
    },
    'coredata.tasks.expiring_roles': {
        'task': 'coredata.tasks.expiring_roles',
        'schedule': crontab(minute='30', hour='7', day_of_week='mon,thu'),
    },
    'dashboard.tasks.photo_password_update_task': {
        'task': 'dashboard.tasks.photo_password_update_task',
        'schedule': crontab(day_of_month="10,20,30", hour=2, minute=0),
    },

    'advisornotes.tasks.cleanup_advising_surveys': {
        'task': 'advisornotes.tasks.cleanup_advising_surveys',
        'schedule': crontab(minute=0, hour='2'),
    },
    'advisornotes.tasks.program_info_for_advisorvisits': {
        'task': 'advisornotes.tasks.program_info_for_advisorvisits',
        'schedule': crontab(minute=0, hour='2'),
    },
    'forum.tasks.send_digests': {
        'task': 'forum.tasks.send_digests',
        'schedule': crontab(hour='*', minute='0'),
    },
    'grad.tasks.update_statuses_to_current': {
        'task': 'grad.tasks.update_statuses_to_current',
        'schedule': crontab(minute=0, hour=3),
    },
    'onlineforms.tasks.waiting_forms_reminder': {
        'task': 'onlineforms.tasks.waiting_forms_reminder',
        'schedule': crontab(day_of_week="1", hour="13", minute="0"),
    },
    'onlineforms.tasks.reject_dormant_initial': {
        'task': 'onlineforms.tasks.reject_dormant_initial',
        'schedule': crontab(hour="18", minute="0"),
    },
    'ra.tasks.expiring_ras_reminder': {
        'task': 'ra.tasks.expiring_ras_reminder',
        'schedule': crontab(minute='0', hour='13'),
    },
    'reminders.tasks.daily_reminders': {
        'task': 'reminders.tasks.daily_reminders',
        'schedule': crontab(minute='0', hour='9'),
    },
    'reports.tasks.run_regular_reports': {
        'task': 'reports.tasks.run_regular_reports',
        'schedule': crontab(hour=9, minute=15),
    },
    'ta.tasks.check_and_execute_reminders': {
        'task': 'ta.tasks.check_and_execute_reminders',
        'schedule': crontab(minute='00', hour='8'),
    },    
}