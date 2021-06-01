# coding=utf-8

import os, sys
from django.core.wsgi import get_wsgi_application
sys.path.append('.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'courses.settings'
application = get_wsgi_application()

from coredata.models import Role, ROLES

roles = ['ADVS', 'ADMN', 'GRAD', 'GRPD', 'REPV', 'SYSA']

sysa = set(r.person for r in Role.objects_fresh.filter(role='SYSA').select_related('person'))

for r in roles:
    print(('\n' + ROLES[r]))
    roles = Role.objects_fresh.filter(role=r).select_related('person', 'unit').order_by('unit__slug', 'person__last_name')
    for rp in roles:
        if rp.person in sysa and r != 'SYSA':
            continue

        if rp.unit.slug == 'univ':
            print('- %s (%s, %s)' % (rp.person.name(), rp.person.userid, rp.person.emplid))
        else:
            print('- %s (%s, %s, %s)' % (rp.person.name(), rp.person.userid, rp.person.emplid, rp.unit.name))
