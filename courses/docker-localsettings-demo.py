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

MORE_ALLOWED_HOSTS = os.environ.get('MORE_ALLOWED_HOSTS', 'coursys-demo.selfip.net coursys-test.selfip.net localhost:8080').strip().split()
CSRF_TRUSTED_ORIGINS = os.environ.get('CSRF_TRUSTED_ORIGINS', 'http://coursys-demo.selfip.net http://coursys-test.selfip.net http://localhost:8080').strip().split()


import os
from django.utils.safestring import mark_safe
SERVER_MESSAGE_INDEX = mark_safe('''<p class="infomessage"><i class="fas fa-info-circle"></i>
    Welcome to the CourSys demo server. You can experiment here consequence-free. You can fake-authenticate as other
    users as needed to explore the system. No emails will be sent by anything here.</p>
''') # , but they will be <a href="http://localhost:8025">visible publicly here</a> if you'd like to inspect them.
SERVER_MESSAGE = mark_safe('''<p class="warningmessage"><i class="fas fa-exclamation-triangle"></i>
    This demo server is publicly available and unauthenticated: no confidential or personally-identifying information
    should be entered anywhere here.
</p>''')

if os.path.isfile('/dynamic_config/server_message_index.html'):
    SERVER_MESSAGE_INDEX = mark_safe(open('/dynamic_config/server_message_index.html', 'rt', encoding='utf-8').read())
if os.path.isfile('/dynamic_config/server_message.html'):
    SERVER_MESSAGE = mark_safe(open('/dynamic_config/server_message.html', 'rt', encoding='utf-8').read())
