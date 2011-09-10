import sys, os, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from coredata.tasks import ping
from celery.exceptions import TimeoutError

res = ping.delay()
try:
    res.get(timeout=30)
except TimeoutError:
    print "Celery ping failed: celeryd probably isn't running."

