from django.conf.urls.defaults import *

COURSE_SLUG_RE = '\d{4}-[a-z]{2,4}-\w{3,4}-[a-z]\d{3}'

urlpatterns = patterns('',
    url(r'^$', 'submission.views.index'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_shortname>.*)/$', 'submission.views.show_components'),
)
