from django.conf.urls.defaults import *
from courselib.urlparts import *

prefix = "(?P<course_slug>" + COURSE_SLUG_RE + ")/(?P<activity_slug>" + ACTIVITY_SLUG_RE + ")"

urlpatterns = patterns('submission.views',
    url(r'^$', 'index'),
    url(r'^' + prefix + '/$', 'show_components'),
    url(r'^' + prefix + '/submit/$', 'add_submission'),
    url(r'^' + prefix + '/history/$', 'show_components_submission_history'),
    url(r'^' + prefix + '/add_component/$', 'add_component'),
    url(r'^' + prefix + '/remove/$', 'confirm_remove'),
    url(r'^' + prefix + '/edit/$', 'edit_single'),
    url(r'^' + prefix + '/download/$', 'download_file'),
    url(r'^' + prefix + '/view/(?P<userid>\w+)/$', 'show_student_submission_staff'),
    url(r'^' + prefix + '/view/(?P<userid>\w+)/history/$', 'show_student_history_staff'),
    url(r'^' + prefix + '/mark/(?P<userid>\w+)/$', 'take_ownership_and_mark'),
)
