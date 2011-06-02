import os, sys, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from coredata.models import *

courses = CourseOffering.objects.filter(semester__name="1114")
instr = itertools.chain(*(c.member_set.filter(role="INST") for c in courses if c.activity_set.count()>0))
print ", ".join(set([i.person.email() for i in instr]))
