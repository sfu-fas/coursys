# from http://michaelangela.wordpress.com/2008/05/07/snippet-to-update-django-tables-to-utf8/

import os, sys, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from django.db import connection
cursor = connection.cursor()
cursor.execute('SHOW TABLES')
results=[]
for row in cursor.fetchall(): results.append(row)
for row in results: cursor.execute('ALTER TABLE %s CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci;' % (row[0]))
