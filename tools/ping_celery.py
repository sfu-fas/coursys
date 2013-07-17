import sys, os, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from coredata.tasks import ping
from celery.exceptions import TimeoutError
from djkombu.models import Message
import time

res = ping.delay()
try:
    # try to run a task
    res.get(timeout=120)
except TimeoutError:
    # if it doesn't return, see if there's other stuff being processed
    count1 = Message.objects.filter(visible=True).count()
    time.sleep(30)
    count2 = Message.objects.filter(visible=True).count()
    
    if count1 == count2:
        print "Celery ping failed: celeryd probably isn't running."
    

