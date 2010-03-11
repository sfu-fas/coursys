from django.conf.urls.defaults import *
#from courses.urls import COURSE_SLUG_RE

COURSE_SLUG_RE = '\d{4}-[a-z]{2,4}-\w{3,4}-[a-z]\d{3}'
ACTIVITY_SLUG_RE = '[\w-]+'

urlpatterns = patterns('',
    url(r'^$', 'marking.views.index'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/$', 'marking.views.list_activities'),        
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>' + ACTIVITY_SLUG_RE + ')/components/$', 'marking.views.manage_activity_components'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>' + ACTIVITY_SLUG_RE + ')/common_problems/$', 'marking.views.manage_common_problems'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>' + ACTIVITY_SLUG_RE + ')/marking/$', 'marking.views.marking'),        
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>' + ACTIVITY_SLUG_RE + ')/mark_summary/$', 'marking.views.mark_summary'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>' + ACTIVITY_SLUG_RE + ')/mark_summary/(?P<filepath>.*)$', 'marking.views.download_marking_attachment'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>' + ACTIVITY_SLUG_RE + ')/mark_history/$', 'marking.views.mark_history'),
)
