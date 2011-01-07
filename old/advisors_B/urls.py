from django.conf.urls.defaults import *

from advisors_B.models import *

urlpatterns = patterns('advisors_B.views',
    (r'^$','index'),
    (r'^(?P<note_id>\d+)/detail/$', 'detail'),
    (r'^(?P<advisor_id>\w+)/(?P<student_id>\w+)/create/$','create'),
    (r'^(?P<advisor_id>\w+)/(?P<student_id>\w+)/submit/$', 'submit'),
    (r'^search_form/$', 'search_form'),
    (r'^search/$', 'search_result'),

)
