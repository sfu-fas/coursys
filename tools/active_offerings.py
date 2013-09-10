import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from grades.models import Activity

activities = Activity.objects.filter(deleted=False, offering__semester__name='1137').select_related('offering')
offerings = set((a.offering for a in activities))
for o in offerings:
    print "%-30s %s" % (o, o.instructors_str())

