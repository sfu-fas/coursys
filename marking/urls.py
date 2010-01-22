from django.conf.urls.defaults import *


urlpatterns = patterns('',
    url(r'^$', 'marking.views.index'),
)
