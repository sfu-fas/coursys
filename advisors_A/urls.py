from django.conf.urls.defaults import *


urlpatterns = patterns( '',
    url(r'^$', 'advisors_A.views.index'),
    url(r'^search/$', 'advisors_A.views.search'),
    url(r'^notes/(?P<empId>\d{9})/$', 'advisors_A.views.display_notes')
)
