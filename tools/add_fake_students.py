import sys, os, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')
import django

# create "objs" by selecting all objects you want to serialize
from coredata.models import *
c = CourseOffering.objects.get(slug="1114-cmpt-383-d100")
students = Person.objects.filter(userid__contains="0bbb")

for s in students:
    try:
        m = Member(person=s, offering=c, role="STUD", credits=3, career="UGRD", added_reason="AUTO")
        #m.save()
    except django.db.utils.IntegrityError:
        pass

