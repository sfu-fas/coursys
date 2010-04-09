# Django settings for courses project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'db.sqlite'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

DATABASE_OPTIONS = {}
if DATABASE_ENGINE == 'mysql':
    # note: CREATE DATABASE <dbname> CHARACTER SET utf8;
    DATABASE_OPTIONS["init_command"] = "SET storage_engine=INNODB"

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
    #'django.contrib.messages.middleware.MessageMiddleware',
    'contrib.messages.middleware.MessageMiddleware', # temp: replace with above after 1.2 release
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django_cas.middleware.CASMiddleware',
)
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'django_cas.backends.CASBackend',
)
TEMPLATE_CONTEXT_PROCESSORS = ("django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    #"django.contrib.messages.context_processors.messages"
    'contrib.messages.context_processors.messages', # temp: replace with above after 1.2 release
    )

ROOT_URLCONF = 'courses.urls'
INTERNAL_IPS = []

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    'templates',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.markup',
    #'django.contrib.messages',
    'contrib.messages', # temp: replace with above after 1.2 release
    'coredata',
    'dashboard',
    'grades',
    'marking',
    'log',
    'groups',
    'submission',

    # for orientation project only
    #'advisors_A',
    #'advisors_B',
)

#MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
MESSAGE_STORAGE = 'contrib.messages.storage.session.SessionStorage' # temp: replace with above after 1.2 release


if DEBUG:
    SUBMISSION_PATH = "submitted_files"
    INSTALLED_APPS = INSTALLED_APPS + ('django.contrib.admin',)
    CACHE_BACKEND = 'locmem://'
else:
    SUBMISSION_PATH = None
    CACHE_BACKEND = '?????'


CAS_SERVER_URL = "https://cas.sfu.ca/cgi-bin/WebObjects/cas.woa/wa/"
if DEBUG:
    CAS_SERVER_URL = "http://lefty.cmpt.sfu.ca/fake-cas/"
LOGIN_URL = "/login/"
LOGOUT_URL = "/logout/"
LOGIN_REDIRECT_URL = "/"
