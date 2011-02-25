# creates initial data for planning module, based on historical offerings

import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append(".")

from coredata.models import *
from planning.models import *

# find all courses in the system from previous semesters
courses = {}
taught = {}
for o in CourseOffering.objects.filter(graded=True):
    key = (o.subject, o.number)
    courses[key] = o.title
    if key not in taught:
        taught[key] = set()
    for i in o.member_set.filter(role="INST"):
        taught[key].add(i.person)

for subj, num in courses:
    # create Course object
    title = courses[(subj, num)]
    cs = Course.objects.filter(subject=subj, number=num)
    if not cs:
        c = Course(subject=subj, number=num, title=title)
        c.save()
    else:
        c = cs[0]

    # add teaching capabilities for previous instructors
    for p in taught[(subj, num)]:
        if not TeachingCapability.objects.filter(course=c, instructor=p):
            t = TeachingCapability(course=c, instructor=p)
            t.save()

