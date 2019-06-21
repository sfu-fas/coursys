from django.conf import global_settings # Django defaults so we can modify them
from django.urls import reverse_lazy
import socket, sys, os
hostname = socket.gethostname()

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
elif hostname == 'courses':
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
    ('Phil Boutros', 'philb@sfu.ca'),
    ('sumo Kindersley', 'sumo@cs.sfu.ca'),
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
    'featureflags',
    'rest_framework',
    'oauth_provider',
    'rest_framework_swagger',
    'django_otp',
    'django_otp.plugins.otp_totp',
    'django_otp.plugins.otp_static',
    'otp',

    'coredata',
    'dashboard',
    'grad',
    'grades',
    'marking',
    'log',
    'groups',
    'submission',
    'discipline',
    'ta',
    'pages',
    'ra',
    'advisornotes',
    'reports',
    'discuss',
    'onlineforms',
    'faculty',
    'tacontracts',
    'api',
    'visas',
    'outreach',
    'sessionals',
    'inventory',
    'relationships',
    'space',
    'reminders',
)
MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'otp.middleware.Authentication2FAMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
OAUTH_AUTHORIZE_VIEW = 'api.views.oauth_authorize'
OAUTH_CALLBACK_VIEW = 'api.views.oauth_callback'
OAUTH_SIGNATURE_METHODS = ['hmac-sha1',]
OAUTH_UNSAFE_REDIRECTS = True
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_oauth.authentication.OAuthAuthentication',
    )
}
SWAGGER_SETTINGS = { "api_version": '1' }

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

# Disable migrations only when running tests.
if 'test' in sys.argv[1:]:
    MIGRATION_MODULES = {}
    for m in INSTALLED_APPS:
        MIGRATION_MODULES[m] = None

# security-related settings
ALLOWED_HOSTS = getattr(localsettings, 'ALLOWED_HOSTS', ['courses.cs.sfu.ca', 'coursys.cs.sfu.ca', 'coursys.sfu.ca', 'fasit.sfu.ca'])
if DEBUG:
    ALLOWED_HOSTS.append('localhost')

SESSION_COOKIE_AGE = 1209600 # 2 weeks
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

PASSWORD_AUTH_AGE = 7*24*3600 # 1 week
TWOFACTOR_AUTH_AGE = 31*24*3600 # 1 month

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
            'HOST': 'localhost',
            'PORT': 3306,
        })

    DATABASES['default'].update(getattr(localsettings, 'DB_CONNECTION', {}))
    DATABASES['default'].update(getattr(secrets, 'DB_CONNECTION', {}))
    if getattr(secrets, 'MORE_DATABASES', None):
        DATABASES.update(secrets.MORE_DATABASES)

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
COMPRESS_CSS_FILTERS = ['compressor.filters.css_default.CssAbsoluteFilter', 'compressor.filters.cssmin.CSSMinFilter']
COMPRESS_JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter']
COMPRESS_ROOT = getattr(localsettings, 'COMPRESS_ROOT', STATIC_ROOT)
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
    HAYSTACK_SIGNAL_PROCESSOR = 'courselib.signals.SelectiveRealtimeSignalProcessor'
    DB_BACKUP_DIR = '/home/coursys/db_backup'

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
    HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.BaseSignalProcessor'
    DB_BACKUP_DIR = os.path.join(BASE_DIR, 'db_backup')

HAYSTACK_SIGNAL_PROCESSOR = getattr(localsettings, 'HAYSTACK_SIGNAL_PROCESSOR', HAYSTACK_SIGNAL_PROCESSOR)
HAYSTACK_CONNECTIONS = getattr(localsettings, 'HAYSTACK_CONNECTIONS', HAYSTACK_CONNECTIONS)
#HAYSTACK_SILENTLY_FAIL = False

# things only relevant to the true production environment
if DEPLOY_MODE == 'production':
    MIDDLEWARE = ['courselib.middleware.MonitoringMiddleware'] + MIDDLEWARE
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SUBMISSION_PATH = '/data/submitted_files'
    BASE_ABS_URL = "https://coursys.sfu.ca"
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend' # changed below if using Celery
    SVN_DB_CONNECT = {'host': '127.0.0.1', 'user': 'svnuser', 'passwd': getattr(secrets, 'SVN_DB_PASS'),
            'db': 'coursesvn', 'port': 4000}

else:
    SUBMISSION_PATH = "submitted_files"
    BASE_ABS_URL = getattr(localsettings, 'BASE_ABS_URL', "http://localhost:8000")
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend' # todo: could use Malm or something
    SVN_DB_CONNECT = None




# should we use the Celery task queue (for sending email, etc)?  Must have celeryd running to process jobs.
USE_CELERY = getattr(localsettings, 'USE_CELERY', DEPLOY_MODE != 'devel')
if USE_CELERY:
    AMPQ_PASSWORD = getattr(secrets, 'AMPQ_PASSWORD', 'supersecretpassword')
    if DEPLOY_MODE != 'devel' or getattr(localsettings, 'DEPLOYED_CELERY_SETTINGS', False):
        # use AMPQ in production, and move email sending to Celery
        CELERY_BROKER_URL = getattr(secrets, 'CELERY_BROKER_URL', "amqp://coursys:%s@localhost:5672/myvhost" % (AMPQ_PASSWORD))
        CELERY_RESULT_BACKEND = 'rpc://'
        CELERY_TASK_RESULT_EXPIRES = 18000 # 5 hours.
    else:
        CELERY_BROKER_URL = getattr(secrets, 'CELERY_BROKER_URL', "amqp://guest:guest@localhost:5672/")
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
    DJANGO_CELERY_BEAT_TZ_AWARE = USE_TZ
    CELERYD_TASK_SOFT_TIME_LIMIT = 1200
    CELERY_ENABLE_UTC = True

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
        'rate_limit' : '30/m',
        'queue': 'email',
        'serializer': 'pickle', # email objects aren't JSON serializable
    }


MAX_SUBMISSION_SIZE = 30000 # kB
CAS_SERVER_URL = "https://cas.sfu.ca/cas/"
CAS_VERSION = '3'
CAS_LOGIN_MSG = None
EMAIL_HOST = 'localhost'
DEFAULT_FROM_EMAIL = 'CourSys <nobody@coursys.sfu.ca>'
DEFAULT_SENDER_EMAIL = 'helpdesk@cs.sfu.ca'
SVN_URL_BASE = "https://punch.cs.sfu.ca/svn/"
SIMS_USER = getattr(secrets, 'SIMS_USER', 'ggbaker')
SIMS_PASSWORD = getattr(secrets, 'SIMS_PASSWORD', '')
SIMS_DB_NAME = "csrpt"
SIMS_DB_SCHEMA = "dbcsown"
EMPLID_API_SECRET = getattr(secrets, 'EMPLID_API_SECRET', '')

#PIWIK_URL = getattr(secrets, 'PIWIK_URL', None)
#PIWIK_TOKEN = getattr(secrets, 'PIWIK_TOKEN', None)
#PIWIK_SITEID = getattr(secrets, 'PIWIK_SITEID', 1)
#PIWIK_CELERY = USE_CELERY
#PIWIK_CELERY_TASK_KWARGS = {'queue': 'batch', 'rate_limit': '5/s', 'max_retries': 6, 'default_retry_delay': 600}
#PIWIK_FAIL_SILENTLY = True
#PIWIK_FORCE_HOST = 'courses.cs.sfu.ca'

BACKUP_REMOTE_URL = getattr(secrets, 'BACKUP_REMOTE_URL', None)
BACKUP_KEY_ID = getattr(secrets, 'BACKUP_KEY_ID', None)
BACKUP_KEY_PASSPHRASE = getattr(secrets, 'BACKUP_KEY_PASSPHRASE', None)

DATE_FORMAT = "D N d Y"
SHORT_DATE_FORMAT = "N d Y"
DATETIME_FORMAT = "D N d Y, H:i"
SHORT_DATETIME_FORMAT = "N d Y, H:i"
GRAD_DATE_FORMAT = "m/d/Y"
GRAD_DATETIME_FORMAT = "m/d/Y H:i"

PASSWORD_LOGIN_URL = reverse_lazy('dashboard:login')
LOGIN_URL = reverse_lazy('otp:login_2fa')
LOGOUT_URL = reverse_lazy('dashboard:logout')
LOGIN_REDIRECT_URL = "/"

DISABLE_REPORTING_DB = getattr(localsettings, 'DISABLE_REPORTING_DB', False)
DO_IMPORTING_HERE = getattr(localsettings, 'DO_IMPORTING_HERE', False)

# Feature flags to temporarily limit server load, aka "feature flags"
# Possible values for the set documented in server-setup/index.html#flags
FEATUREFLAGS_LOADER = 'featureflags.loaders.settings_loader'
FEATUREFLAGS_DISABLED_VIEW = 'courselib.auth.service_unavailable'
FEATUREFLAGS_DISABLE = set([])
FEATUREFLAGS_PANIC_DISABLE = set(['course_browser', 'sims', 'feeds', 'photos'])
FEATUREFLAGS_PANIC_TIMEOUT = 300

LOGGING = getattr(localsettings, 'LOGGING', {'version': 1,'disable_existing_loggers': False})

AUTOSLUG_SLUGIFY_FUNCTION = 'courselib.slugs.make_slug'

FORCE_CAS = getattr(localsettings, 'FORCE_CAS', False)
if not FORCE_CAS and (DEPLOY_MODE != 'production' or DEBUG) and hostname != 'courses':
    AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',)
    MIDDLEWARE.remove('django_cas_ng.middleware.CASMiddleware')
    PASSWORD_LOGIN_URL = "/fake_login"
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
    MIDDLEWARE = MIDDLEWARE + ['debug_toolbar.middleware.DebugToolbarMiddleware']
    INTERNAL_IPS = getattr(localsettings, 'INTERNAL_IPS', [])
    #DEBUG_TOOLBAR_CONFIG = {
    #    'INTERCEPT_REDIRECTS': False,
    #}
