from django.conf.urls import url

from courselib.urlparts import SLUG_RE
from . import views


COMPONENT_SLUG = '(?P<thread_slug>' + SLUG_RE + ')'


forum_patterns = [ # prefix /COURSE_SLUG/forum/
    url(r'^(?P<number>\d+)?$', views.index, name='index'),
    url(r'^new', views.new_thread, name='new_thread'),
    #url(r'^view/' + COMPONENT_SLUG, views.view_thread, name='view_thread'),
]