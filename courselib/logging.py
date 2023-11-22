# Want to use LoggingMiddleware? In localsettings.py:
# from courselib.logging import POSSIBLE_LOGGING_CONFIG as LOGGING

from courses import localsettings
from courses import secrets

RABBITMQ_USER = getattr(localsettings, 'RABBITMQ_USER', 'coursys')
RABBITMQ_PASSWORD = getattr(secrets, 'RABBITMQ_PASSWORD', 'the_rabbitmq_password')
RABBITMQ_HOSTPORT = getattr(localsettings, 'RABBITMQ_HOSTPORT', 'localhost:5672')
RABBITMQ_VHOST = getattr(localsettings, 'RABBITMQ_VHOST', 'myvhost')

RABBITMQ_HOST, RABBITMQ_PORT = RABBITMQ_HOSTPORT.split(':')

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
        'rabbitmq': {
            'level': 'DEBUG',
            'class': 'python_logging_rabbitmq.RabbitMQHandlerOneWay',
            'host': RABBITMQ_HOST,
            'port': int(RABBITMQ_PORT),
            'username': RABBITMQ_USER,
            'password': RABBITMQ_PASSWORD,
            'exchange': 'log',
            'declare_exchange': True,
            'connection_params': {'virtual_host': RABBITMQ_VHOST, 'connection_attempts': 4, 'socket_timeout': 5000},
            'expiration': str(7 * 24 * 3600 * 1000),
        },
    },
    'loggers': {
        'django-logging': {
            'handlers': ['mail_admins', 'rabbitmq'],
            'level': 'DEBUG',
        }
    }
}