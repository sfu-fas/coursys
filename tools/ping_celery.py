import sys, os, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from coredata.tasks import ping
from celery.exceptions import TimeoutError
from celery.task.control import inspect
import time

res = ping.delay()
try:
    # try to run a task
    res.get(timeout=600)
except TimeoutError:
    # if it doesn't return, see if there's other stuff being processed
    i = inspect()
    stat1 = i.reserved()
    time.sleep(10)
    stat2 = i.reserved()
    
    if stat1 == stat2:
        print "Celery ping failed: celeryd probably isn't running."
        print "The inspection of the queue revealed this:", stat1

