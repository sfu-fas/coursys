# This is mounted in the app container as courses/localsettings.py, overriding anything in that actual file.

DEPLOY_MODE="proddev"
COMPRESS_ENABLED=False
#USE_CELERY=True
#DISABLE_REPORTING_DB=False
ALLOWED_HOSTS = ['localhost']
#FORCE_MEMCACHED = True

DB_CONNECTION = {
    'HOST': 'db',
}
HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
            'PATH': '/tmp/whoosh_index',
        }
}