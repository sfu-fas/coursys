from django.urls import re_path as url
from courselib.urlparts import ACTIVITY_SLUG, SLUG_RE
import groups.views as groups_views

group_patterns = [ # prefix /COURSE_SLUG/groups/
    url(r'^$', groups_views.groupmanage, name='groupmanage'),
    url(r'^new$', groups_views.create, name='create'),
    url(r'^assignStudent$', groups_views.assign_student, name='assign_student'),
    url(r'^submit$', groups_views.submit, name='submit'),
    url(r'^photos', groups_views.group_photos, name='group_photos'),
    url(r'^data$', groups_views.group_data, name='group_data'),
    url(r'^for/' + ACTIVITY_SLUG + '$', groups_views.groupmanage, name='groupmanage'),
    url(r'^invite/(?P<group_slug>' + SLUG_RE + ')$', groups_views.invite, name='invite'),
    url(r'^join/(?P<group_slug>' + SLUG_RE + ')$', groups_views.join, name='join'),
    url(r'^reject/(?P<group_slug>' + SLUG_RE + ')$', groups_views.reject, name='reject'),
    url(r'^(?P<group_slug>' + SLUG_RE + ')/$', groups_views.view_group, name='view_group'),
    url(r'^(?P<group_slug>' + SLUG_RE + ')/remove$', groups_views.remove_student, name='remove_student'),
    url(r'^(?P<group_slug>' + SLUG_RE + ')/add$', groups_views.assign_student, name='assign_student'),
    url(r'^(?P<group_slug>' + SLUG_RE + ')/rename$', groups_views.change_name, name='change_name'),
]
