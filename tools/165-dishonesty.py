import os, sys, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'courses.settings'
sys.path.append('.')

from discipline.models import *
from coredata.queries import *
from collections import Counter

cases = DisciplineCaseInstrStudent.objects.filter(owner__userid='ggbaker', offering__number='165',
        offering__semester__name__in=['1137','1141','1144']).exclude(penalty__in=['NONE', 'WAIT']).select_related('student')
students = [c.student for c in cases]
print(len(students))

student_data = [more_personal_info(p.emplid, ['citizen'])['citizen'] for p in students]
print(Counter(student_data))
