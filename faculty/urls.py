from django.conf.urls import patterns, url
from courselib.urlparts import USERID_OR_EMPLID

urlpatterns = patterns('',
    url(r'^$', 'faculty.views.index'),
    url(r'^summary/' + USERID_OR_EMPLID+ '/$', 'faculty.views.summary'),
)
