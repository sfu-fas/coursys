import os, sys
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')
sys.path.append('external')

from grad.models import GradStudent

for gs in GradStudent.objects.all():
    print(gs)
    gs.update_status_fields()
