from django.conf.urls import url

from courselib.urlparts import SLUG_RE
from . import views


POST_NUMBER = r'(?P<post_number>\d+)'


forum_patterns = [ # prefix /COURSE_SLUG/forum/
    url(r'^$', views.summary, name='summary'),
    url(r'^'+POST_NUMBER+'$', views.view_thread, name='view_thread'),
    url(r'^thread-list', views.thread_list, name='thread_list'),
    url(r'^new', views.new_thread, name='new_thread'),
    url(r'^'+POST_NUMBER+r'/react/(?P<reaction>\w+)$', views.react, name='react'),
    url(r'^anon', views.anon_identity, name='anon_identity'),
]