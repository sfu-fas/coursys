# per http://celery.readthedocs.org/en/latest/django/first-steps-with-django.html
import os
import datetime
from celery import Celery

import sys
assert sys.version_info >= (3, 5)

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'courses.settings')

app = Celery('courses')
# https://github.com/celery/django-celery-beat/issues/80#issuecomment-329448732
app.now = datetime.datetime.now

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(('Request: {0!r}'.format(self.request)))
