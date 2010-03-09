from django.conf.urls.defaults import *

COURSE_SLUG_RE = '\d{4}-[a-z]{2,4}-\w{3,4}-[a-z]\d{3}'

urlpatterns = patterns('',
    url(r'^$', 'submission.views.index'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>\w+)/$', 'submission.views.show_components'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>\w+)/submit/$', 'submission.views.add_submission'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>\w+)/history/$', 'submission.views.show_components_submission_history'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>\w+)/add_component/$', 'submission.views.add_component'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>\w+)/remove/$', 'submission.views.confirm_remove'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>\w+)/edit/$', 'submission.views.edit_single'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>\w+)/download/$', 'submission.views.download_file'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>\w+)/view/(?P<userid>\w+)/$', 'submission.views.show_student_submission_staff'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/(?P<activity_slug>\w+)/view/(?P<userid>\w+)/history/$', 'submission.views.show_student_history_staff'),
)
