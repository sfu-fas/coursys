import sys, os
sys.path.append(".")
sys.path.append("..")
os.environ['DJANGO_SETTINGS_MODULE'] = 'courses.settings'

from grad.models import *
import datetime

sem = Semester.objects.get(name='1147')
statuses = GradStatus.objects.filter(student__program__unit__label='CMPT', start__name='1147', status='CONF', student__current_status='CONF', hidden=False)
students = set(s.student for s in statuses)
for gs in students:
    print gs
    s = GradStatus(student=gs, status='ACTI', start=sem, start_date=datetime.date(2014, 9, 2))
    s.save()