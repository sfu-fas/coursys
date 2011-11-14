import os, sys, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from coredata.models import *
from discipline.models import *

crs = CourseOffering.objects.get(slug="2011fa-cmpt-120-x1")
cases = DisciplineCaseInstrStudent.objects.filter(offering=crs)

def get_instructors(crs):
    members = Member.objects.filter(offering=crs, role="INST")
    return [m.person for m in members]

# make sure the case owner is from the students original section
for case in cases:
    section = case.membership().get_origsection()
    instrs = get_instructors(section)
    if case.owner not in instrs:
        case.owner = instrs[0]
        case.save()
