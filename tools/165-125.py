import os, sys, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from coredata.models import *

offerings = CourseOffering.objects.filter(semester__name="1137", subject="CMPT", number="165")
#offerings = offerings.filter(section="D200")
students = Member.objects.filter(role="STUD", offering__in=offerings).select_related('person')
people = [m.person for m in students]

prev_cmpt = Member.objects.filter(person__in=people,
        offering__subject="CMPT", role="STUD")
#prev_cmpt = prev_cmpt.exclude(offering__semester__name="1137")
prev_125 = prev_cmpt.filter(offering__number="125")
prev_126 = prev_cmpt.filter(offering__number="126")

print(prev_125.count() + prev_126.count())
print(students.count())


