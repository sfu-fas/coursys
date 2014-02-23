import socket, sys, os
hostname = socket.gethostname()

DEBUG = hostname != 'courses'
TEMPLATE_DEBUG = DEBUG
DEPLOYED = hostname == 'courses'

PROJECT_DIR = os.path.normpath(os.path.dirname(os.path.dirname(__file__)))

# add ./external directory to search path so we find modules there
sys.path.append( PROJECT_DIR )
sys.path.append( os.path.join(PROJECT_DIR, 'external') )

ADMINS = (
    ('Greg Baker', 'ggbaker@sfu.ca'),
    ('Curtis Lassam', 'classam@sfu.ca'),
    ('sumo Kindersley', 'sumo@cs.sfu.ca'),
)

MANAGERS = ADMINS

if DEPLOYED:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'course_management',
            'USER': 'courseuser',
            'PASSWORD': '?????',
            'HOST': '127.0.0.1',
            'PORT': '4000',
            'CONN_MAX_AGE': 3600,
            #'OPTIONS': {"init_command": "SET storage_engine=INNODB;"} # needed only for initial table creation
            'OPTIONS': {"init_command": "SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;"}, # Celeryd misbehaves if not set
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'db.sqlite',
            'CONN_MAX_AGE': 3600,
        }
    }

# Local time zone for this installation.
TIME_ZONE = 'America/Vancouver'
USE_TZ = False
LANGUAGE_CODE = 'en'
SITE_ID = 1
USE_I18N = True
MEDIA_ROOT = os.path.join(PROJECT_DIR, 'uploads')
MEDIA_URL = '/media/'
#ADMIN_MEDIA_PREFIX = '/adminmedia/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'w@h_buddoh5**%79%0x&7h0ro2tol+-7vz=p*kn_g+0qcw8krr'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'courselib.middleware.ExceptionIgnorer',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_cas.middleware.CASMiddleware',
    'courselib.impersonate.ImpersonateMiddleware',
    'courselib.mobile_detection.MobileDetectionMiddleware'
)
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'django_cas.backends.CASBackend',
)
TEMPLATE_CONTEXT_PROCESSORS = ("django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.contrib.messages.context_processors.messages",
    'django.core.context_processors.request',
    'django.core.context_processors.static',
    'dashboard.context.media',
    )

ROOT_URLCONF = 'courses.urls'
INTERNAL_IPS = ('127.0.0.1',)
TEST_RUNNER="courselib.testrunner.AdvancedTestSuiteRunner"
TEST_EXCLUDE = ('django',)

TEMPLATE_DIRS = (
    os.path.join(PROJECT_DIR, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    #'django.contrib.markup',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'south',
    'compressor',

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
    'mobile',
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
if DEBUG:
    #INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar',)
    #MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + ('debug_toolbar.middleware.DebugToolbarMiddleware',)
    INSTALLED_APPS = INSTALLED_APPS + ('django.contrib.admin',)
    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
    }

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
SESSION_COOKIE_AGE = 86400 # 24 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
X_FRAME_OPTIONS = 'DENY'

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(PROJECT_DIR, 'media')
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)
COMPRESS_ENABLED = not DEBUG
#COMPRESS_ENABLED = True
COMPRESS_CSS_FILTERS = ['compressor.filters.css_default.CssAbsoluteFilter', 'compressor.filters.cssmin.CSSMinFilter']
COMPRESS_JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter']


if DEPLOYED:
    MIDDLEWARE_CLASSES = ('courselib.middleware.MonitoringMiddleware',) + MIDDLEWARE_CLASSES
    SUBMISSION_PATH = '/data/submitted_files'
    CACHES = { 'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:22122',
    } }
    BASE_ABS_URL = "https://courses.cs.sfu.ca"
    SESSION_COOKIE_SECURE = True
    DB_PASS_FILE = "/home/ggbaker/dbpass"
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend' # changed below if using Celery
    SVN_DB_CONNECT = {'host': '127.0.0.1', 'user': 'svnuser', 'passwd': '????',
            'db': 'coursesvn', 'port': 4000}
else:
    #MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + ('contrib.profiling.ProfileMiddleware',)
    SUBMISSION_PATH = "submitted_files"
    #INSTALLED_APPS = INSTALLED_APPS + ('django.contrib.admin',)
    CACHES = { 'default': {
        #'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        #'LOCATION': '127.0.0.1:11211',
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    } }
    BASE_ABS_URL = "http://localhost:8000"
    DB_PASS_FILE = "./dbpass"
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend' # changed below if using Celery
    SVN_DB_CONNECT = None

# should we use the Celery job queue (for sending email, etc)?  Must have celeryd running to process jobs.
USE_CELERY = DEPLOYED
#USE_CELERY = True
if USE_CELERY:
    os.environ["CELERY_LOADER"] = "django"
    INSTALLED_APPS = INSTALLED_APPS + (
        'djcelery',
        'djcelery_email',
        )
    BROKER_URL = "amqp://coursys:supersecretpassword@localhost:5672/myvhost"
    CELERY_ACCEPT_CONTENT = ['json', 'pickle']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'

    CELERY_DEFAULT_QUEUE = 'batch'
    CELERY_QUEUES = { # any new queues should be reflected in the /etc/defaults/celery setup
        'batch': {},
        'email': {},
        'fast': {}, # only jobs that need to run soon, and finish quickly should go in this queue
        'photo': {}, # separate queue for photo fetching, so we can enforce the max-5-concurrent-requests requirement
        'sims': {}, # SIMS/reporting database queries
    }
    CELERY_SEND_TASK_ERROR_EMAILS = True
    CELERY_EMAIL_TASK_CONFIG = {
        'rate_limit' : '30/m',
        'queue': 'email',
        'serializer': 'pickle',
    }
    CELERY_EMAIL_BACKEND = EMAIL_BACKEND
    EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'
    SERVER_EMAIL = 'ggbaker@sfu.ca'

if 'DEVELOPER' in os.environ:
    ACTIVE_DEVELOPER = os.environ['DEVELOPER']
else:
    ACTIVE_DEVELOPER = 'ggbaker'

CAS_SERVER_URL = "https://cas.sfu.ca/cgi-bin/WebObjects/cas.woa/wa/"
EMAIL_HOST = 'mailgate.sfu.ca'
DEFAULT_FROM_EMAIL = 'nobody@courses.cs.sfu.ca'
DEFAULT_SENDER_EMAIL = 'helpdesk@cs.sfu.ca'
SVN_URL_BASE = "https://punch.cs.sfu.ca/svn/"
SIMS_USER = ACTIVE_DEVELOPER
SIMS_DB_NAME = "csrpt"
SIMS_DB_SCHEMA = "dbcsown"
DATE_FORMAT = "D N d Y"
SHORT_DATE_FORMAT = "N d Y"
DATETIME_FORMAT = "D N d Y, H:i"
SHORT_DATETIME_FORMAT = "N d Y, H:i"
GRAD_DATE_FORMAT = "m/d/Y"
GRAD_DATETIME_FORMAT = "m/d/Y H:i"

LOGIN_URL = "/login/"
LOGOUT_URL = "/logout/"
LOGIN_REDIRECT_URL = "/"
DISABLE_REPORTING_DB = False

# Feature flags to temporarily limit server load, aka "feature flags"
# Possible values for the set documented in server-setup/index.html#flags
DISABLED_FEATURES = set([])

AUTOSLUG_SLUGIFY_FUNCTION = 'courselib.slugs.make_slug'

if not DEPLOYED and DEBUG and hostname != 'courses':
    #CAS_SERVER_URL = "http://lefty.cmpt.sfu.ca/fake-cas/"
    AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',)
    MIDDLEWARE_CLASSES = list(MIDDLEWARE_CLASSES)
    MIDDLEWARE_CLASSES.remove('django_cas.middleware.CASMiddleware')
    MIDDLEWARE_CLASSES = tuple(MIDDLEWARE_CLASSES)
    LOGIN_URL = "/fake_login"
    LOGOUT_URL = "/fake_logout"
    DISABLE_REPORTING_DB = True # never do reporting DB access if users aren't really authenticated

REPORT_CACHE_LOCATION = "/tmp/report_cache"

#EXTRA_MIDDLEWARE_CLASSES = ()
try:
    from local_settings import *
except ImportError:
    pass

#MIDDLEWARE_CLASSES = EXTRA_MIDDLEWARE_CLASSES + MIDDLEWARE_CLASSES
