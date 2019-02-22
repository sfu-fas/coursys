# coding=utf-8

import os, sys
from django.core.wsgi import get_wsgi_application
sys.path.append('.')
os.environ['DJANGO_SETTINGS_MODULE'] = 'courses.settings'
application = get_wsgi_application()

from django.db import transaction
import itertools
from grad.models import GradStatus

all_statuses = GradStatus.objects.filter(hidden=False).order_by('student_id')
for gs_id, statuses in itertools.groupby(all_statuses, key=lambda s: s.student_id):
    statuses = list(statuses)
    statuses = [s for s in statuses if 'sims_source' in s.config]
    statuses.sort(key=lambda s: (hash(tuple(s.config['sims_source'])), s.created_at))
    with transaction.atomic():
        for sims_source, sts in itertools.groupby(statuses, key=lambda s: s.config['sims_source']):
            sts = list(sts)
            for st in sts[1:]:
                print('deleting', st)
                st.config['bad_import_deletion'] = True
                st.hidden = True
                #st.save()




