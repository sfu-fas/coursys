DEPLOY_MODE = 'proddev'

#DEBUG_TOOLBAR = True
#INTERNAL_IPS = ['127.0.0.1']
#DISABLE_REPORTING_DB = False

import os
MOSS_DISTRIBUTION_PATH = os.path.join(os.environ['HOME'], 'moss')
DB_BACKUP_DIR = '/data/db_backup'
SUBMISSION_PATH = '/data/submitted_files'
