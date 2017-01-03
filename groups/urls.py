from django.conf.urls import url
from courselib.urlparts import ACTIVITY_SLUG, SLUG_RE

group_patterns = [ # prefix /COURSE_SLUG/groups/
    url(r'^$', 'groups.views.groupmanage', name='groupmanage'),
    url(r'^new$', 'groups.views.create', name='create'),
    url(r'^assignStudent$', 'groups.views.assign_student', name='assign_student'),
    url(r'^submit$', 'groups.views.submit', name='submit'),
    url(r'^data$', 'groups.views.group_data', name='group_data'),
    url(r'^for/' + ACTIVITY_SLUG + '$', 'groups.views.groupmanage', name='groupmanage'),
    url(r'^invite/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.invite', name='invite'),
    url(r'^join/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.join', name='join'),
    url(r'^reject/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.reject', name='reject'),
    url(r'^(?P<group_slug>' + SLUG_RE + ')/$', 'groups.views.view_group', name='view_group'),
    url(r'^(?P<group_slug>' + SLUG_RE + ')/remove$', 'groups.views.remove_student', name='remove_student'),
    url(r'^(?P<group_slug>' + SLUG_RE + ')/add$', 'groups.views.assign_student', name='assign_student'),
    url(r'^(?P<group_slug>' + SLUG_RE + ')/rename$', 'groups.views.change_name', name='change_name'),
]
