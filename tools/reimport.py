import os, sys, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from coredata.importer import import_one_semester
import time

for strm in ['1134', '1131', '1127', '1124', '1121', '1117', '1114', '1111', '1107', '1104', '1101']:
    import_one_semester(strm)
    time.sleep(100) 
