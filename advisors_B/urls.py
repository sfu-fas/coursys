from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
from advisors_B.models import *
admin.autodiscover()

urlpatterns = patterns('',
    (r'^advisors_B/$', 'advisors_B.views.index'),
    (r'^advisors_B/search/$', 'advisors_B.views.search'),
    (r'^advisors_B/display/$', 'advisors_B.views.display_note'),
    (r'^advisors_B/add/$', 'advisors_B.views.add_note'),
)
