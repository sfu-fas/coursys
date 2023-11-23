# Want to use LoggingMiddleware? In localsettings.py:
# from courselib.logging import POSSIBLE_LOGGING_CONFIG as LOGGING

from courses import localsettings
from courses import secrets

POSSIBLE_LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'raw': {
            'format': '%(message)s',
        },
        'django.server': {  # from https://docs.djangoproject.com/en/dev/ref/logging/#default-logging-definition
            '()': 'django.utils.log.ServerFormatter',
            'format': '[{server_time}] {message}',
            'style': '{',
        }
    },
    'handlers': {
#        'logfile': {
#            'level': 'DEBUG',
#            'class': 'logging.handlers.RotatingFileHandler',
#            'filename': './coursys.log',
#            'maxBytes': 1024*1024*15,  # 15MB
#            'backupCount': 10,
#            'formatter': 'raw',
#        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'django.server'
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
        },
    },
    'loggers': {
        'django-logging': {
            'handlers': ['mail_admins'],
            'level': 'DEBUG',
        }
    }
}