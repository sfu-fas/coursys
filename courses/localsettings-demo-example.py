DEPLOY_MODE = 'proddev'

BASE_ABS_URL = 'https://coursys-demo.selfip.net'
MORE_ALLOWED_HOSTS = ['coursys-demo.selfip.net']
MORE_DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/coursys/db.sqlite',
    }
}

import os
MOSS_DISTRIBUTION_PATH = os.path.join(os.environ['HOME'], 'moss')
DB_BACKUP_DIR = os.path.join(os.environ['COURSYS_DATA_ROOT'], 'db_backup')
SUBMISSION_PATH = os.path.join(os.environ['COURSYS_DATA_ROOT'], 'submitted_files')

from django.utils.safestring import mark_safe
SERVER_MESSAGE_INDEX = mark_safe('''<p class="infomessage"><i class="fas fa-info-circle"></i>
    Welcome to the CourSys demo server. You can experiment here consequence-free. You can fake-authenticate as other
    users as needed to explore the system. No emails will be sent by anything here, but they will be
    <a href="http://localhost:8025">visible publicly here</a> if you'd like to inspect them.</p>
''')
SERVER_MESSAGE = mark_safe('''<p class="warningmessage"><i class="fas fa-exclamation-triangle"></i>
    This demo server is publicly available and unauthenticated: no confidential or personally-identifying information
    should be entered anywhere here.
</p>''')

# mail to a smtp4dev server
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 2525
EMAIL_USE_SSL = False