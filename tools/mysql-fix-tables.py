# from http://michaelangela.wordpress.com/2008/05/07/snippet-to-update-django-tables-to-utf8/
# http://dev.mysql.com/doc/refman/5.0/en/converting-tables-to-innodb.html

import os, sys, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from django.db import connection
cursor = connection.cursor()
cursor.execute('SHOW TABLES')
results=[]
for row in cursor.fetchall(): results.append(row)
#for row in results: 

for row in results:
    table = row[0]
    print(table)
    #cursor.execute('ALTER TABLE %s ENGINE=InnoDB' % (table))
    #cursor.execute('ALTER TABLE %s CONVERT TO CHARACTER SET utf8 COLLATE utf8_general_ci;' % (table))
