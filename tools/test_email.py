import sys, os, itertools
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
sys.path.append('.')

from django.core.mail import send_mail

for i in range(2):
    send_mail('This is a test message', 'Hello.', 'ggbaker@sfu.ca',
        ['ggbaker@sfu.ca'], fail_silently=False)


import djkombu.models
djkombu.models.Message.objects.cleanup()
