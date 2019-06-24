# This is mounted in the app container as courses/localsettings.py, overriding anything in that actual file.

DEPLOY_MODE="proddev"
COMPRESS_ENABLED=True
USE_CELERY=True
#DISABLE_REPORTING_DB=False
ALLOWED_HOSTS = ['localhost']
FORCE_MEMCACHED = True
NPM_ROOT_PATH = '/npm/'

DB_CONNECTION = {
    'HOST': 'db',
}
COMPRESS_ROOT = '/static/static'
MEMCACHED_HOST = 'memcache:11211'
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
        'URL': 'http://solr:8983/solr/coursys',
        'ADMIN_URL': 'http://solr:8983/solr/admin/cores',
    },
}
