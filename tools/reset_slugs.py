import os, sys, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from coredata.models import *
import datetime

#courses = CourseOffering.objects.filter(semester__start__gt=datetime.date.today())
courses = CourseOffering.objects.all()
for c in courses:
    print(c.slug)
    c.slug = None
    c.save()
