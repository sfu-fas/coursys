import sys, os, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from coredata.models import *
from dashboard.models import *
import django.db.utils

members = Member.objects.filter(offering__slug="1114-cmpt-470-d100").exclude(role="DROP")

# make sure the .config property of all of those was converted to a dict when JSON was loaded.
for m in members:
    p = m.person
    c = UserConfig(user=p, key="newsitems", value={'email': True})
    try:
        c.save()
    except django.db.utils.IntegrityError:
        pass
