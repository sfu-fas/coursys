from django.conf.urls.defaults import *

COURSE_SLUG_RE = '\d{4}-[a-z]{2,4}-\w{3,4}-[a-z]\d{3}'
urlpatterns = patterns('',
	url(r'^$', 'groups.views.index'),
	url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/$', 'groups.views.groupmanage'),
	url(r'^create/$', 'groups.views.create'),
	url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/join/(?P<groupname>\w+)/$', 'groups.views.join'),
	url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/joinconfirm/$', 'groups.views.joinconfirm'),
)
