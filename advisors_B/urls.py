from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from advisors_B.models import *
from django.conf import settings
admin.autodiscover()

urlpatterns = patterns('advisors_B.views',
    (r'^$','index'),
    (r'^(?P<note_id>\d+)/detail/$', 'detail'),
    (r'^(?P<advisor_id>\w+)/(?P<student_id>\w+)/create/$','create'),
    (r'^searchresult/$', 'search_result'),

)