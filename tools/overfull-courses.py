import os, sys, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from coredata.models import *
offerings = CourseOffering.objects.exclude(component='CAN') \
    .filter(semester__name__in=['1141'], owner__slug='cmpt')
for o in offerings:
    if o.enrl_tot == 0:
        continue
    ratio = 1.0*o.wait_tot/o.enrl_tot
#    if ratio > 0.3:
    print(o, o.enrl_tot, o.wait_tot)
