import sys, os
sys.path.append(".")
sys.path.append("..")
os.environ['DJANGO_SETTINGS_MODULE'] = 'courses.settings'

from grad.models import *
import datetime

semestername = '1147'

sem = Semester.objects.get(name=semestername)
statuses = GradStatus.objects\
        .filter(student__program__unit__label='CMPT', start__name=semestername,
        status='CONF', student__current_status='CONF', hidden=False)\
        .select_related('student')
students = set(s.student for s in statuses)
newer_status_students = set(s.student for s in GradStatus.objects
        .filter(student__program__unit__label='CMPT', student__in=students, start__name__gt=semestername)
        .select_related('student'))
students -= newer_status_students

for gs in students:
    print(gs)
    s = GradStatus(student=gs, status='ACTI', start=sem, start_date=datetime.date(2014, 9, 2))
    s.save()