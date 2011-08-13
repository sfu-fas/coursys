import socket, sys, os
hostname = socket.gethostname()

DEBUG = hostname != 'courses'
TEMPLATE_DEBUG = DEBUG
DEPLOYED = hostname == 'courses'

# add ./external directory to search path so we find modules there
sys.path.append( os.path.join(os.path.dirname(__file__), 'external') )

ADMINS = (
    ('Greg Baker', 'ggbaker@sfu.ca'),
)

MANAGERS = ADMINS

if DEPLOYED:
    DATABASE_ENGINE = 'mysql'
    DATABASE_NAME = 'course_management'
    DATABASE_USER = 'courseuser'
    DATABASE_PASSWORD = '?????'
    DATABASE_HOST = '127.0.0.1'
    DATABASE_PORT = '4000'
else:
    DATABASE_ENGINE = 'sqlite3'
    DATABASE_NAME = 'db.sqlite'
    DATABASE_USER = ''
    DATABASE_PASSWORD = ''
    DATABASE_HOST = ''
    DATABASE_PORT = ''

DATABASE_OPTIONS = {}
if DATABASE_ENGINE == 'mysql':
    #DATABASE_OPTIONS["init_command"] = "SET storage_engine=INNODB;" # needed only for initial table creation
    DATABASE_OPTIONS["init_command"] = "SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED;" # Celeryd misbehaves if not set

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Vancouver'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = 'media'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/adminmedia/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'w@h_buddoh5**%79%0x&7h0ro2tol+-7vz=p*kn_g+0qcw8krr'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_cas.middleware.CASMiddleware',
    #'throttle.CacheThrottler',
    'courselib.impersonate.ImpersonateMiddleware',
    'courselib.mobile_detection.MobileDetectionMiddleware'
)
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'django_cas.backends.CASBackend',
)
TEMPLATE_CONTEXT_PROCESSORS = ("django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.contrib.messages.context_processors.messages",
    'django.core.context_processors.request',
    )

ROOT_URLCONF = 'courses.urls'
INTERNAL_IPS = ('127.0.0.1',)
TEST_RUNNER="courselib.testrunner.AdvancedTestSuiteRunner"
TEST_EXCLUDE = ('django',)

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    'templates',
)
if DEPLOYED:
    TEMPLATE_DIRS = TEMPLATE_DIRS + ('/home/ggbaker/courses/templates',)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.markup',
    'django.contrib.messages',
    'south',
    'coredata',
    'dashboard',
    'grades',
    'marking',
    'log',
    'groups',
    'submission',
    'planning',
    'discipline',
    'mobile',
    #'advisors',

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

if DEPLOYED:
    MIDDLEWARE_CLASSES = ('courselib.exception_middleware.ExceptionMiddleware',) + MIDDLEWARE_CLASSES
    SUBMISSION_PATH = '/data/submitted_files'
    CACHE_BACKEND = 'memcached://127.0.0.1:22122/'
    BASE_ABS_URL = "https://courses.cs.sfu.ca"
    SESSION_COOKIE_SECURE = True
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend' # changed below if using Celery
    SVN_SERVER_IP = 'svn.cs.sfu.ca'
else:
    #MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + ('contrib.profiling.ProfileMiddleware',)
    SUBMISSION_PATH = "submitted_files"
    #INSTALLED_APPS = INSTALLED_APPS + ('django.contrib.admin',)
    CACHE_BACKEND = 'locmem://'
    BASE_ABS_URL = "http://localhost:8000"
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend' # changed below if using Celery
    SVN_SERVER_IP = '127.0.0.1'

# should we use the Celery job queue (for sending email)?  Must have celeryd running to process jobs.
USE_CELERY = DEPLOYED
if USE_CELERY:
    os.environ["CELERY_LOADER"] = "django"
    INSTALLED_APPS = INSTALLED_APPS + (
        'djkombu',
        'djcelery',
        'djcelery_email',
        )
    BROKER_BACKEND = "djkombu.transport.DatabaseTransport"
    DJKOMBU_POLLING_INTERVAL = 10
    CELERY_QUEUES = {
        "celery": {},
        "email": {},
    }
    CELERY_SEND_TASK_ERROR_EMAILS = True
    CELERY_EMAIL_TASK_CONFIG = {
        'queue' : 'email',
        'rate_limit' : '30/m',
    }
    CELERY_EMAIL_BACKEND = EMAIL_BACKEND
    EMAIL_BACKEND = 'djcelery_email.backends.CeleryEmailBackend'


CAS_SERVER_URL = "https://cas.sfu.ca/cgi-bin/WebObjects/cas.woa/wa/"
EMAIL_HOST = 'mailgate.sfu.ca'
DEFAULT_FROM_EMAIL = 'nobody@courses.cs.sfu.ca'
DEFAULT_SENDER_EMAIL = 'helpdesk@cs.sfu.ca'

if not DEPLOYED and DEBUG and hostname != 'courses':
    CAS_SERVER_URL = "http://lefty.cmpt.sfu.ca/fake-cas/"
LOGIN_URL = "/login/"
LOGOUT_URL = "/logout/"
LOGIN_REDIRECT_URL = "/"
