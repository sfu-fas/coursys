import os
DEPLOY_MODE = 'production'

DB_CONNECTION = {
    'HOST': os.environ['DB_HOST'],
    'USER': os.environ['DB_USER'],
    'NAME': os.environ['DB_NAME'],
}

RABBITMQ_HOSTPORT = f'rabbitmq:5672'
RABBITMQ_USER = os.environ['RABBITMQ_USER']
RABBITMQ_VHOST = os.environ['RABBITMQ_VHOST']

MEMCACHED_HOST = 'memcached'
HAYSTACK_HOST = 'elasticsearch'
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp4dev'
MOSS_DISTRIBUTION_PATH = './moss'

SUBMISSION_PATH = '/submitted_files'
DB_BACKUP_DIR = '/db_backups'

# from django.utils.safestring import mark_safe
# SERVER_MESSAGE_INDEX = mark_safe('''<p class="infomessage"><i class="fas fa-info-circle"></i> Info on the index page.</p>''')
# SERVER_MESSAGE = mark_safe('''<p class="warningmessage"><i class="fas fa-exclamation-triangle"></i> Warning on every page</p>''')
