from django.conf.urls.defaults import *


urlpatterns = patterns( '',
    url(r'^$', 'advisors_A.views.index'),
    url(r'^search/$', 'advisors_A.views.search'),
    url(r'^notes/(?P<empId>\d{9})/$', 'advisors_A.views.display_notes'),
    url(r'^notes/(?P<empId>\d{9})/add_note/$', 'advisors_A.views.add_note'),
    url(r'^notes/(?P<empId>\d{9})/(?P<noteId>\d+)/hide/(?P<attr>\w+)/$', 'advisors_A.views.hide_note'),
)
