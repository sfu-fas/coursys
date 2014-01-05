import sys, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'courses.settings'
sys.path.append('.')

from coredata.tasks import ping
from celery.exceptions import TimeoutError

# run a task
res = ping.apply_async()
try:
    # try to get the result
    res.get(timeout=60)

except TimeoutError:
    print "Celery ping task failed: celeryd probably isn't running."

