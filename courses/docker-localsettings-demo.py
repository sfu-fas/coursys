import os
DEPLOY_MODE = 'proddev'

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
MORE_ALLOWED_HOSTS = ['localhost:8080']
CSRF_TRUSTED_ORIGINS = ['http://localhost:8080']
