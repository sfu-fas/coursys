# options devels might want to set
#DEPLOY_MODE="proddev"
#COMPRESS_ENABLED=True
#USE_CELERY=True
#DISABLE_REPORTING_DB=False
#ALLOWED_HOSTS = ['localhost']
#FORCE_MEMCACHED = True
#PIWIK_URL = 'https://.../piwik/piwik.php'
#PIWIK_TOKEN = '123456789abcdef' # find at Piwik -> user -> API
#PIWIK_SITEID = 1

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': '/tmp/debug.log',
            'formatter':'standard',
        },
    },
    'loggers': {
        'coredata.models': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
