from django.conf.urls import patterns, url
from courselib.urlparts import USERID_OR_EMPLID, UNIT_SLUG

FACULTY_SLUG = UNIT_SLUG + '/' + USERID_OR_EMPLID

urlpatterns = patterns('',
    url(r'^$', 'faculty.views.index'),
    url(r'^' + FACULTY_SLUG + '/summary$', 'faculty.views.summary'),
    url(r'^' + FACULTY_SLUG + '/otherinfo', 'faculty.views.otherinfo'),
)
