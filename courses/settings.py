from django.conf import global_settings # Django defaults so we can modify them
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
TEMPLATE_DEBUG = DEBUG


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
sys.path.append( BASE_DIR )
sys.path.append( os.path.join(BASE_DIR, 'external') )

ADMINS = (
    ('Greg Baker', 'ggbaker@sfu.ca'),
    ('Curtis Lassam', 'classam@sfu.ca'),
    ('sumo Kindersley', 'sumo@cs.sfu.ca'),
)
SERVER_EMAIL = 'ggbaker@sfu.ca'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    #'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'south',
    'compressor',
    'haystack',
    'djcelery',
    'djcelery_email',
    'featureflags',

    'coredata',
    'dashboard',
    'grad',
    'grades',
    'marking',
    'log',
    'groups',
    'submission',
    #'planning',
    'discipline',
    'ta',
    'pages',
    'ra',
    'advisornotes',
    'alerts',
    'reports',
    'discuss',
    #'booking',
    #'techreq',
    'onlineforms',
    'faculty',
    'gpaconvert',
)
MIDDLEWARE_CLASSES = global_settings.MIDDLEWARE_CLASSES + (
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'courselib.middleware.ExceptionIgnorer',
    'django_cas.middleware.CASMiddleware',
    'courselib.impersonate.ImpersonateMiddleware',
)
TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
)
TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
    'dashboard.context.media',
)
AUTHENTICATION_BACKENDS = (
    'django_cas.backends.CASBackend',
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

# security-related settings
ALLOWED_HOSTS = getattr(localsettings, 'ALLOWED_HOSTS', ['courses.cs.sfu.ca'])
SESSION_COOKIE_AGE = 86400 # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# database config
if DEPLOY_MODE in ['production', 'proddev']:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'CONN_MAX_AGE': 3600,
            'OPTIONS': {"init_command": "SET storage_engine=INNODB;"} # actually needed only for initial table creation
        }
    }

    if DEPLOY_MODE == 'proddev':
        #
        DATABASES['default'].update({
            'NAME': 'coursys',
            'USER': 'coursysuser',
            'PASSWORD': 'coursyspassword',
            'HOST': 'localhost',
            'PORT': 3306,
        })

    DATABASES['default'].update(getattr(localsettings, 'DB_CONNECTION', {}))
    DATABASES['default'].update(getattr(secrets, 'DB_CONNECTION', {}))

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
STATIC_URL = '/media/'
STATIC_ROOT = os.path.join(BASE_DIR, 'media')
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    #'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)
COMPRESS_ENABLED = getattr(localsettings, 'COMPRESS_ENABLED', DEPLOY_MODE != 'devel')
COMPRESS_CSS_FILTERS = ['compressor.filters.css_default.CssAbsoluteFilter', 'compressor.filters.cssmin.CSSMinFilter']
COMPRESS_JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter']
COMPRESS_ROOT = os.path.join(BASE_DIR, 'media')


# production-like vs development settings
if DEPLOY_MODE in ['production', 'proddev']:
    CACHES = { 'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    } }
    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
            'URL': 'http://localhost:8983/solr'
            #'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
            #'URL': 'http://127.0.0.1:9200/',
            #'INDEX_NAME': 'haystack',
        },
    }
    USE_CELERY = True

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
            #'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
            'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
            'PATH': os.path.join(BASE_DIR, 'whoosh_index'),
            #'ENGINE': 'haystack.backends.solr_backend.SolrEngine',
            #'URL': 'http://localhost:8983/solr'
        },
    }
    USE_CELERY = False


# things only relevant to the true production environment
if DEPLOY_MODE == 'production':
    MIDDLEWARE_CLASSES = ('courselib.middleware.MonitoringMiddleware',) + MIDDLEWARE_CLASSES
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SUBMISSION_PATH = '/data/submitted_files'
    BASE_ABS_URL = "https://courses.cs.sfu.ca"
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend' # changed below if using Celery
    SVN_DB_CONNECT = {'host': '127.0.0.1', 'user': 'svnuser', 'passwd': getattr(secrets, 'SVN_DB_PASS'),
            'db': 'coursesvn', 'port': 4000}

else:
    SUBMISSION_PATH = "submitted_files"
    BASE_ABS_URL = "http://localhost:8000"
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend' # todo: could use Malm or something
    SVN_DB_CONNECT = None




# should we use the Celery task queue (for sending email, etc)?  Must have celeryd running to process jobs.
USE_CELERY = getattr(localsettings, 'USE_CELERY', USE_CELERY)
if USE_CELERY:
    os.environ["CELERY_LOADER"] = "django"
    if DEPLOY_MODE != 'devel':
        # use AMPQ in production, and move email sending to Celery
        AMPQ_PASSWORD = getattr(secrets, 'AMPQ_PASSWORD', 'supersecretpassword')
        BROKER_URL = getattr(secrets, 'BROKER_URL', "amqp://coursys:%s@localhost:5672/myvhost" % (AMPQ_PASSWORD))
        CELERY_RESULT_BACKEND = 'amqp'
        CELERY_TASK_RESULT_EXPIRES = 18000 # 5 hours.
    else:
        # use Kombo (aka the Django database) in devel
        BROKER_URL = getattr(secrets, 'BROKER_URL', "django://")
        INSTALLED_APPS = INSTALLED_APPS + ("kombu.transport.django",)

    CELERY_EMAIL = getattr(localsettings, 'CELERY_EMAIL', DEPLOY_MODE != 'devel')
    if CELERY_EMAIL:
        CELERY_EMAIL_BACKEND = EMAIL_BACKEND
        EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'
    
    CELERYBEAT_SCHEDULER = "djcelery.schedulers.DatabaseScheduler"
    CELERY_ACCEPT_CONTENT = ['json', 'pickle']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'

    CELERY_DEFAULT_QUEUE = 'batch'
    CELERY_QUEUES = { # any new queues should be reflected in the /etc/defaults/celery setup
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
CAS_SERVER_URL = "https://cas.sfu.ca/cgi-bin/WebObjects/cas.woa/wa/"
EMAIL_HOST = 'mailgate.sfu.ca'
DEFAULT_FROM_EMAIL = 'nobody@courses.cs.sfu.ca'
DEFAULT_SENDER_EMAIL = 'helpdesk@cs.sfu.ca'
SVN_URL_BASE = "https://punch.cs.sfu.ca/svn/"
SIMS_USER = getattr(secrets, 'SIMS_USER', 'ggbaker')
SIMS_PASSWORD = getattr(secrets, 'SIMS_PASSWORD', '')
SIMS_DB_NAME = "csrpt"
SIMS_DB_SCHEMA = "dbcsown"
AMAINT_DB_PASSWORD = getattr(secrets, 'AMAINT_DB_PASSWORD', '')

DATE_FORMAT = "D N d Y"
SHORT_DATE_FORMAT = "N d Y"
DATETIME_FORMAT = "D N d Y, H:i"
SHORT_DATETIME_FORMAT = "N d Y, H:i"
GRAD_DATE_FORMAT = "m/d/Y"
GRAD_DATETIME_FORMAT = "m/d/Y H:i"

LOGIN_URL = "/login/"
LOGOUT_URL = "/logout/"
LOGIN_REDIRECT_URL = "/"
DISABLE_REPORTING_DB = getattr(localsettings, 'DISABLE_REPORTING_DB', False)

# Feature flags to temporarily limit server load, aka "feature flags"
# Possible values for the set documented in server-setup/index.html#flags
FEATUREFLAGS_LOADER = 'featureflags.loaders.settings_loader'
FEATUREFLAGS_DISABLED_VIEW = 'courselib.auth.service_unavailable'
FEATUREFLAGS_DISABLE = set([])
FEATUREFLAGS_PANIC_DISABLE = set(['course_browser', 'sims', 'feeds'])


AUTOSLUG_SLUGIFY_FUNCTION = 'courselib.slugs.make_slug'

if DEPLOY_MODE != 'production' or DEBUG or hostname != 'courses':
    AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',)
    MIDDLEWARE_CLASSES = list(MIDDLEWARE_CLASSES)
    MIDDLEWARE_CLASSES.remove('django_cas.middleware.CASMiddleware')
    MIDDLEWARE_CLASSES = tuple(MIDDLEWARE_CLASSES)
    LOGIN_URL = "/fake_login"
    LOGOUT_URL = "/fake_logout"
    DISABLE_REPORTING_DB = getattr(localsettings, 'DISABLE_REPORTING_DB', True)

REPORT_CACHE_LOCATION = "/tmp/report_cache"

#INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar',)
#MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + ('debug_toolbar.middleware.DebugToolbarMiddleware',)
#DEBUG_TOOLBAR_CONFIG = {
#    'INTERCEPT_REDIRECTS': False,
#}

#try:
#    from local_settings import *
#except ImportError:
#    pass

