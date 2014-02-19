import os, sys, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from coredata.importer import import_one_semester
import time

semesters = []
for yr in range(102, 113):
    for s in [1,4,7]:
        semesters.append("%03i%i" % (yr, s))

for strm in semesters:
    #if strm < '1074':
    #    continue
    import_one_semester(strm)
    time.sleep(100) 
