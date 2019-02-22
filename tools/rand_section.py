import sys, os, itertools, random
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')
import django

from coredata.models import *
c = CourseOffering.objects.get(slug="1111-cmpt-165-d100")

# put all members into a random lab section
for m in c.member_set.filter(role="STUD"):
    print(m)
    sec = "D1%02i" % (random.randint(1,4))
    m.labtut_section = sec
    #m.save()

