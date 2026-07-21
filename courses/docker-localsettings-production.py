import os
import tomllib
from django.utils.safestring import mark_safe

config = tomllib.load(open('/run/secrets/app-config', 'rb'))

DEPLOY_MODE = config['system']['deploy_mode']
SECRET_KEY = config['system']['django_secret']

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

SERVE_HOSTS = os.environ['SERVE_HOSTS'].split()
USER_PROTOCOL = os.environ['USER_PROTOCOL']
USER_PORT = os.environ['USER_PORT']

assert DEPLOY_MODE == 'production'
SIMS_DB_SERVER = config['external']['csrpt_server']
DO_IMPORTING_HERE = True
FORCE_CAS = True
EMPLID_API_SECRET = config['external']['emplid_api_secret']
# AMAINT_DB_PASSWORD = config['external']['amaint_password']  # unused with current API?

# SERVER_MESSAGE_INDEX = mark_safe('''<p class="infomessage"><i class="fas fa-info-circle"></i> Info on the index page.</p>''')
# SERVER_MESSAGE = mark_safe('''<p class="warningmessage"><i class="fas fa-exclamation-triangle"></i> Warning on every page</p>''')

if os.path.isfile('/dynamic_config/server_message_index.html'):
    SERVER_MESSAGE_INDEX = mark_safe(open('/dynamic_config/server_message_index.html', 'rt', encoding='utf-8').read())
if os.path.isfile('/dynamic_config/server_message.html'):
    SERVER_MESSAGE = mark_safe(open('/dynamic_config/server_message.html', 'rt', encoding='utf-8').read())
