from django.conf.urls import url
from courselib.urlparts import ACTIVITY_SLUG, SLUG_RE

group_patterns = [ # prefix /COURSE_SLUG/groups/
    url(r'^$', 'groups.views.groupmanage'),
    url(r'^new$', 'groups.views.create'),
    url(r'^assignStudent$', 'groups.views.assign_student'),
    url(r'^submit$', 'groups.views.submit'),
    url(r'^for/' + ACTIVITY_SLUG + '$', 'groups.views.groupmanage'),
    url(r'^invite/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.invite'),
    url(r'^join/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.join'),
    url(r'^reject/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.reject'),
    url(r'^(?P<group_slug>' + SLUG_RE + ')/remove$', 'groups.views.remove_student'),
    url(r'^(?P<group_slug>' + SLUG_RE + ')/add$', 'groups.views.assign_student'),
    url(r'^(?P<group_slug>' + SLUG_RE + ')/rename$', 'groups.views.change_name'),
]