import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from grades.models import Activity

activities = Activity.objects.filter(deleted=False, offering__semester__name__in=['1131','1134','1137']).select_related('offering')
activities = activities.exclude(offering__owner__label="CMPT")
offerings = set((a.offering for a in activities))
for o in offerings:
    print("%-30s %s" % (o, o.instructors_str()))

