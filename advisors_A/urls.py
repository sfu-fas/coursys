from django.conf.urls.defaults import *


urlpatterns = patterns( '',
    url(r'^$', 'advisors_A.views.index'),
    url(r'^search/$', 'advisors_A.views.search'),
)
