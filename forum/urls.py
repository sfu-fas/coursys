from django.conf.urls import url

from courselib.urlparts import SLUG_RE
from . import views


COMPONENT_SLUG = '(?P<thread_slug>' + SLUG_RE + ')'


forum_patterns = [ # prefix /COURSE_SLUG/forum/
    url(r'^$', views.index, name='index'),
    url(r'^(?P<post_number>\d+)?$', views.view_thread, name='view_thread'),
    url(r'^new', views.new_thread, name='new_thread'),
    url(r'^anon', views.anon_identity, name='anon_identity'),
]