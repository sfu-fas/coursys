import sys, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'courses.settings'
sys.path.append('.')

from oauth_provider.models import Consumer
from oauth_provider.consts import ACCEPTED
from django.contrib.auth.models import User
from api.models import ConsumerInfo

KEY = '9fdce0e111a1489eb5a42eab7a84306b'
SECRET = 'liqutXmqJpKmetfs'

def create_consumer():
    ConsumerInfo.objects.filter(consumer__key=KEY).delete()
    Consumer.objects.filter(key=KEY).delete()

    c = Consumer(name='Example Consumer', description='Consumer to do some demos with', status=ACCEPTED,
                 user=User.objects.get(username='ggbaker'), xauth_allowed=False,
                 key=KEY, secret=SECRET)
    #c.generate_random_codes()
    c.save()
    i = ConsumerInfo(consumer=c)
    i.admin_contact = 'the_developer@example.com'
    i.permissions = ['courses', 'grades']
    i.save()
    return c

c = create_consumer()
print c.__dict__