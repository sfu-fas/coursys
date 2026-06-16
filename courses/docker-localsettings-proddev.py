import os
import tomllib
config = tomllib.load(open('/run/secrets/app-config', 'rb'))

DEPLOY_MODE = config['system']['deploy_mode']

DB_CONNECTION = {
    'HOST': config['database']['hostname'],
    'USER': config['database']['username'],
    'PASSWORD': config['database']['password'],
    'NAME': config['database']['name'],
}

RABBITMQ_USER = config['rabbitmq']['username']
RABBITMQ_PASSWORD = config['rabbitmq']['password']
RABBITMQ_VHOST = config['rabbitmq']['vhost']
ELASTICSEARCH_PASSWORD = config['elasticsearch']['password']
NPM_ROOT_PATH = '/build'

EMAIL_HOST = 'smtp4dev'
try:
    NTP_REFERENCE = config['system']['ntp_reference']
except KeyError:
    pass

MORE_ALLOWED_HOSTS = os.environ.get('MORE_ALLOWED_HOSTS', 'localhost:8080').strip().split()
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://localhost:8080').strip().split()

# from django.utils.safestring import mark_safe
# SERVER_MESSAGE_INDEX = mark_safe('''<p class="infomessage"><i class="fas fa-info-circle"></i> Info on the index page.</p>''')
# SERVER_MESSAGE = mark_safe('''<p class="warningmessage"><i class="fas fa-exclamation-triangle"></i> Warning on every page</p>''')
