import sys, os, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from coredata.models import CourseOffering, Member
from grades.models import Activity

objs = itertools.chain(
        CourseOffering.objects.all(),
        Member.objects.all(),
        Activity.objects.all(),
        )

# make sure the .config property of all of those was converted to a dict when JSON was loaded.
for o in objs:
    assert(isinstance(o.config, dict))
