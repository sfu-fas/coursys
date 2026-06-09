DEPLOY_MODE = 'production'

DO_IMPORTING_HERE = True
FORCE_CAS = True

import tomllib
config = tomllib.load(open('/run/secrets/app-config', 'rb'))

DB_CONNECTION = {
    'HOST': config['database']['hostname'],
    'USER': config['database']['username'],
    'NAME': config['database']['name'],
}

RABBITMQ_USER = config['rabbitmq']['username']
RABBITMQ_VHOST = config['rabbitmq']['vhost']

SIMS_DB_SERVER = config['external']['csrpt_server']

# from django.utils.safestring import mark_safe
# SERVER_MESSAGE_INDEX = mark_safe('''<p class="infomessage"><i class="fas fa-info-circle"></i> Info on the index page.</p>''')
# SERVER_MESSAGE = mark_safe('''<p class="warningmessage"><i class="fas fa-exclamation-triangle"></i> Warning on every page</p>''')
