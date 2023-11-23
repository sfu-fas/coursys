from django.conf import global_settings # Django defaults so we can modify them
from django.urls import reverse_lazy
import socket, sys, os
hostname = socket.gethostname()
assert sys.version_info >= (3, 7)  # some logic assumes the insertion-ordered dicts from Python 3.7+

try:
    from . import localsettings
except ImportError:
    # not there? Assume the defaults are okay
    localsettings = None

try:
    from . import secrets
except ImportError:
    # not there? Hope we're not in production and continue
    secrets = None

# set overall deployment personality

if getattr(localsettings, 'DEPLOY_MODE', None):
    DEPLOY_MODE = localsettings.DEPLOY_MODE
elif hostname == 'courses':  # TODO: this is no longer the correct condition
    # full production mode
    DEPLOY_MODE = 'production'
elif False:
    # production-like development environment
    DEPLOY_MODE = 'proddev'
else:
    # standard development environment
    DEPLOY_MODE = 'devel'

#print "DEPLOY_MODE: ", DEPLOY_MODE

DEBUG = DEPLOY_MODE != 'production'

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append( BASE_DIR )
sys.path.append( os.path.join(BASE_DIR, 'external') )

ADMINS = (
    ('Greg Baker', 'ggbaker@sfu.ca'),
    ('sumo Kindersley', 'sumo@cs.sfu.ca'),
    ('FAS Software Developer', 'fas_developer@sfu.ca'),
    ('Renee Chong', 'renee_chong@sfu.ca'),
)
SERVER_EMAIL = 'ggbaker@sfu.ca'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_cas_ng',
    'compressor',
    'haystack',
    'djcelery_email',
    'django_celery_beat',
    'formtools',
    'coredata',
    'dashboard',
    'grad',
    'grades',
    'marking',
    'log',
    'groups',
    'submission',
    'discipline',
    'quizzes',
    'ta',
    'pages',
    'ra',
    'advisornotes',
    'reports',
    'discuss',
    'onlineforms',
    'faculty',
    'tacontracts',
    'visas',
    'outreach',
    'sessionals',
    'inventory',
    'relationships',
    'space',
    'reminders',
    'forum',
)
MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'courselib.middleware.LoggingMiddleware',
    'courselib.middleware.ExceptionIgnorer',
    'django_cas_ng.middleware.CASMiddleware',
    'courselib.impersonate.ImpersonateMiddleware',
    'courselib.csp.CSPMiddleware',
]
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'dashboard.context.media',
                'courselib.csp.context_processor']},
    },
]

AUTHENTICATION_BACKENDS = (
    'django_cas_ng.backends.CASBackend',
)


# basic app setup
ROOT_URLCONF = 'courses.urls'
WSGI_APPLICATION = 'courses.wsgi.application'
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
LANGUAGE_CODE = 'en'
TIME_ZONE = 'America/Vancouver'
USE_I18N = False
USE_L10N = False
USE_TZ = False
FIXTURE_DIRS = [os.path.join(BASE_DIR, 'fixtures')]
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Disable migrations only when running tests.
if 'test' in sys.argv[1:]:
    MIGRATION_MODULES = {}
    for m in INSTALLED_APPS:
        MIGRATION_MODULES[m] = None

# security-related settings
CANONICAL_HOST = 'coursys.sfu.ca'  # the one true hostname to forward to
SERVE_HOSTS = ['coursys.sfu.ca', 'fasit.sfu.ca']  # hosts where we actually serve pages
SERVE_HOSTS.extend(getattr(localsettings, 'MORE_SERVE_HOSTS', []))
REDIRECT_HOSTS = ['courses.cs.sfu.ca', 'coursys.cs.sfu.ca']  # hosts that forward to the coursys.sfu.ca domain
ALLOWED_HOSTS = getattr(localsettings, 'ALLOWED_HOSTS', SERVE_HOSTS + REDIRECT_HOSTS)
if DEBUG:
    ALLOWED_HOSTS.append('localhost')
ALLOWED_HOSTS.extend(getattr(localsettings, 'MORE_ALLOWED_HOSTS', []))

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 14*24*3600  # 14 days
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
PRE_EXPIRE_AGE = 6*24*3600  # 6 days: expire how long before SESSION_COOKIE_AGE at a convenient time. Handled by coredata.tasks.expire_sessions_conveniently

X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
CSRF_TRUSTED_ORIGINS = getattr(localsettings, 'CSRF_TRUSTED_ORIGINS', [])

# database config
if DEPLOY_MODE in ['production', 'proddev']:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            #'CONN_MAX_AGE': 360,
            'OPTIONS': {
                "init_command": "SET default_storage_engine=INNODB, character_set_client=utf8mb4, character_set_connection=utf8mb4, character_set_results=utf8mb4, collation_connection=utf8mb4_unicode_ci, collation_server=utf8mb4_unicode_ci;",
                'charset': 'utf8mb4',
            }
        }
    }

    # Celery (and other long-idle manage.py tasks) can't have CONN_MAX_AGE set. Only set for gunicorn processes.
    # See https://code.djangoproject.com/ticket/21597
    gunicorn_process = 'SERVER_SOFTWARE' in os.environ and os.environ['SERVER_SOFTWARE'].startswith('gunicorn/')
    if gunicorn_process:
        DATABASES['default']['CONN_MAX_AGE'] = 3600

    if DEPLOY_MODE == 'proddev':
        DATABASES['default'].update({
            'NAME': 'coursys',
            'USER': 'coursysuser',
            'PASSWORD': 'coursyspassword',
            'HOST': '127.0.0.1',
            'PORT': 3306,
        })

    DATABASES['default'].update(getattr(localsettings, 'DB_CONNECTION', {}))
    DATABASES['default'].update(getattr(secrets, 'DB_CONNECTION', {}))
    if getattr(localsettings, 'MORE_DATABASES', None):
        DATABASES.update(localsettings.MORE_DATABASES)

    INSTALLED_APPS = INSTALLED_APPS + ('dbdump',)

else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'db.sqlite',
        }
    }

if DEPLOY_MODE == 'production':
    SECRET_KEY = secrets.SECRET_KEY
else:
    SECRET_KEY = 'a'*50



# static file settings
STATIC_URL = '/static/'
if 'COURSYS_STATIC_DIR' in os.environ:
    STATIC_ROOT = os.path.join(os.environ['COURSYS_STATIC_DIR'], 'static')
else:
    STATIC_ROOT = os.path.join(BASE_DIR, '..', 'static', 'static')

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'npm.finders.NpmFinder',
    'compressor.finders.CompressorFinder',
)
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'media'),
)
COMPRESS_ENABLED = getattr(localsettings, 'COMPRESS_ENABLED', DEPLOY_MODE != 'devel')
COMPRESS_FILTERS = {
    'css': ['compressor.filters.css_default.CssAbsoluteFilter', 'compressor.filters.cssmin.CSSMinFilter'],
    'js': ['compressor.filters.jsmin.JSMinFilter']
}
COMPRESS_ROOT = getattr(localsettings, 'COMPRESS_ROOT', STATIC_ROOT)
COMPRESS_STORAGE = 'courselib.compress.CompressorFileStorage'
NPM_ROOT_PATH = getattr(localsettings, 'NPM_ROOT_PATH', '.')

# production-like vs development settings
if DEPLOY_MODE in ['production', 'proddev']:
    CACHES = { 'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    } }
    if getattr(localsettings, 'MEMCACHED_HOST', None):
        CACHES['default']['LOCATION'] = localsettings.MEMCACHED_HOST
    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'courselib.elasticsearch_backend.CustomElasticsearchSearchEngine',
            'URL': 'http://127.0.0.1:9200/',
            'INDEX_NAME': 'haystack',
            'TIMEOUT': 60,
        },
    }
    DB_BACKUP_DIR = getattr(localsettings, 'DB_BACKUP_DIR', os.path.join(os.environ.get('COURSYS_DATA_ROOT', '.'), 'db_backup'))

else:
    CACHES = { 'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    } }
    if getattr(localsettings, 'FORCE_MEMCACHED', False):
        CACHES = { 'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': '127.0.0.1:11211',
        } }
    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
            'PATH': os.path.join(BASE_DIR, 'whoosh_index'),
        },
    }
    DB_BACKUP_DIR = getattr(localsettings, 'DB_BACKUP_DIR', os.path.join(BASE_DIR, 'db_backup'))

HAYSTACK_SIGNAL_PROCESSOR = getattr(localsettings, 'HAYSTACK_SIGNAL_PROCESSOR', 'haystack.signals.BaseSignalProcessor')
HAYSTACK_CONNECTIONS = getattr(localsettings, 'HAYSTACK_CONNECTIONS', HAYSTACK_CONNECTIONS)
#HAYSTACK_SILENTLY_FAIL = False

# things only relevant to the true production environment
if DEPLOY_MODE == 'production':
    MIDDLEWARE = ['courselib.middleware.MonitoringMiddleware'] + MIDDLEWARE
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SUBMISSION_PATH = getattr(localsettings, 'SUBMISSION_PATH', '/filestore/prod/submitted_files')
    BASE_ABS_URL = "https://coursys.sfu.ca"
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend' # changed below if using Celery
    #SVN_DB_CONNECT = {'host': '127.0.0.1', 'user': 'svnuser', 'passwd': getattr(secrets, 'SVN_DB_PASS', ''),
    #        'db': 'coursesvn', 'port': 4000}
    SVN_DB_CONNECT = None

elif DEPLOY_MODE == 'proddev':
    MIDDLEWARE = ['courselib.middleware.MonitoringMiddleware'] + MIDDLEWARE
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    #SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SUBMISSION_PATH = getattr(localsettings, 'SUBMISSION_PATH', '/data/submitted_files')
    BASE_ABS_URL = getattr(localsettings, 'BASE_ABS_URL', "https://localhost:8443")
    EMAIL_BACKEND = getattr(localsettings, 'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
    SVN_DB_CONNECT = None

else:
    SUBMISSION_PATH = getattr(localsettings, 'SUBMISSION_PATH', "submitted_files")
    BASE_ABS_URL = getattr(localsettings, 'BASE_ABS_URL', "http://localhost:8000")
    EMAIL_BACKEND = getattr(localsettings, 'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend')
    SVN_DB_CONNECT = None


# should we use the Celery task queue (for sending email, etc)?  Must have celeryd running to process jobs.
USE_CELERY = getattr(localsettings, 'USE_CELERY', DEPLOY_MODE != 'devel')
if USE_CELERY:
    RABBITMQ_USER = getattr(localsettings, 'RABBITMQ_USER', 'coursys')
    RABBITMQ_PASSWORD = getattr(secrets, 'RABBITMQ_PASSWORD', 'the_rabbitmq_password')
    RABBITMQ_HOSTPORT = getattr(localsettings, 'RABBITMQ_HOSTPORT', 'localhost:5672')
    RABBITMQ_VHOST = getattr(localsettings, 'RABBITMQ_VHOST', 'myvhost')

    CELERY_BROKER_URL = 'amqp://%s:%s@%s/%s' % (RABBITMQ_USER, RABBITMQ_PASSWORD, RABBITMQ_HOSTPORT, RABBITMQ_VHOST)
    CELERY_BROKER_URL = getattr(secrets, 'CELERY_BROKER_URL', CELERY_BROKER_URL)
    CELERY_RESULT_BACKEND = 'rpc://'
    CELERY_TASK_RESULT_EXPIRES = 18000 # 5 hours.

    CELERY_EMAIL = getattr(localsettings, 'CELERY_EMAIL', DEPLOY_MODE != 'devel')
    if CELERY_EMAIL:
        CELERY_EMAIL_BACKEND = EMAIL_BACKEND
        EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'

    CELERY_ACCEPT_CONTENT = ['json', 'pickle']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'
    from courses import celery_schedule
    CELERY_BEAT_SCHEDULE = celery_schedule.CELERY_BEAT_SCHEDULE
    DJANGO_CELERY_BEAT_TZ_AWARE = USE_TZ
    CELERYD_TASK_SOFT_TIME_LIMIT = 1200
    CELERY_ENABLE_UTC = False
    CELERY_TIMEZONE = TIME_ZONE
    CELERY_TASK_ALWAYS_EAGER = False

    CELERY_TASK_DEFAULT_QUEUE = 'batch'
    CELERY_TASK_QUEUES = { # any new queues should be reflected in the /etc/defaults/celery setup
        'batch': {}, # possibly-slow batch-mode tasks
        'email': {}, # email sending
        'fast': {}, # only jobs that need to run soon, and finish quickly should go in this queue
        'photo': {}, # separate queue for photo fetching, so we can enforce the max-5-concurrent-requests requirement
        'sims': {}, # SIMS/reporting database queries
    }
    CELERY_SEND_TASK_ERROR_EMAILS = True
    CELERY_EMAIL_TASK_CONFIG = {
        'rate_limit' : '60/m',
        'queue': 'email',
        'serializer': 'pickle', # email objects aren't JSON serializable
        # retry-on-failure config: be very liberal in queuing failed mail...
        'default_retry_delay': 1800, # retry every half hour
        'max_retries': 48*3,         # ... for 3 days
    }

MAX_SUBMISSION_SIZE = 30000 # kB
CAS_SERVER_URL = "https://cas.sfu.ca/cas/"
CAS_VERSION = '3'
CAS_LOGIN_MSG = None
CAS_CHECK_NEXT = False
EMAIL_HOST = getattr(localsettings, 'EMAIL_HOST', 'smtpserver.sfu.ca')
EMAIL_PORT = getattr(localsettings, 'EMAIL_PORT', 25)
EMAIL_USE_SSL = getattr(localsettings, 'EMAIL_USE_SSL', False)
DEFAULT_FROM_EMAIL = 'CourSys <nobody@coursys.sfu.ca>'
DEFAULT_SENDER_EMAIL = 'helpdesk@cs.sfu.ca'
SVN_URL_BASE = "https://punch.cs.sfu.ca/svn/"
SIMS_DB_SERVER = getattr(localsettings, 'SIMS_DB_SERVER', '')
SIMS_DB_NAME = getattr(localsettings, 'SIMS_DB_NAME', 'CSRPT')
SIMS_USER = getattr(secrets, 'SIMS_USER', 'ggbaker')  # TODO: remove after DB2 transition
SIMS_PASSWORD = getattr(secrets, 'SIMS_PASSWORD', '')  # TODO: remove after DB2 transition
SIMS_DB_SCHEMA = "dbcsown"  # TODO: remove after DB2 transition

EMPLID_API_SECRET = getattr(secrets, 'EMPLID_API_SECRET', '')
MOSS_DISTRIBUTION_PATH = getattr(localsettings, 'MOSS_DISTRIBUTION_PATH', None)
SERVER_MESSAGE_INDEX = getattr(localsettings, 'SERVER_MESSAGE_INDEX', '')
SERVER_MESSAGE = getattr(localsettings, 'SERVER_MESSAGE', '')

DATE_FORMAT = "D N d Y"
SHORT_DATE_FORMAT = "N d Y"
DATETIME_FORMAT = "D N d Y, H:i"
SHORT_DATETIME_FORMAT = "N d Y, H:i"
GRAD_DATE_FORMAT = "m/d/Y"
GRAD_DATETIME_FORMAT = "m/d/Y H:i"

LOGIN_URL = reverse_lazy('dashboard:login')
LOGOUT_URL = reverse_lazy('dashboard:logout')
LOGIN_REDIRECT_URL = "/"

DISABLE_REPORTING_DB = getattr(localsettings, 'DISABLE_REPORTING_DB', False)
DO_IMPORTING_HERE = getattr(localsettings, 'DO_IMPORTING_HERE', False)
NTP_REFERENCE = getattr(localsettings, 'NTP_REFERENCE', 'ns2.sfu.ca' if DEPLOY_MODE == 'production' else 'pool.ntp.org')

LOGGING = getattr(localsettings, 'LOGGING', {'version': 1,'disable_existing_loggers': False})

AUTOSLUG_SLUGIFY_FUNCTION = 'courselib.slugs.make_slug'

FORCE_CAS = getattr(localsettings, 'FORCE_CAS', False)
if not FORCE_CAS and (DEPLOY_MODE != 'production' or DEBUG) and hostname != 'courses':
    AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',)
    MIDDLEWARE.remove('django_cas_ng.middleware.CASMiddleware')
    LOGIN_URL = "/fake_login"
    LOGOUT_URL = "/fake_logout"
    DISABLE_REPORTING_DB = getattr(localsettings, 'DISABLE_REPORTING_DB', True)

# For security reasons, when we're live, we don't want to keep potentially 
#  sensitive user data in /tmp for longer than the space of one run. 
REPORT_CACHE_LOCATION = "/tmp/report_cache"
REPORT_CACHE_CLEAR = True
if DEPLOY_MODE == 'production':
    REPORT_CACHE_CLEAR = True


DEBUG_TOOLBAR = getattr(localsettings, 'DEBUG_TOOLBAR', False)
if DEBUG_TOOLBAR:
    INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar',)
    MIDDLEWARE = MIDDLEWARE + ['debug_toolbar.middleware.DebugToolbarMiddleware', 'courselib.middleware.NonHtmlDebugToolbarMiddleware']
    INTERNAL_IPS = getattr(localsettings, 'INTERNAL_IPS', ['127.0.0.1'])
    #DEBUG_TOOLBAR_CONFIG = {
    #    'INTERCEPT_REDIRECTS': False,
    #}
