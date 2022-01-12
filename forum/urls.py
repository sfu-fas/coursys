from django.urls import re_path as url

from . import views


POST_NUMBER = r'(?P<post_number>\d+)'


forum_patterns = [ # prefix /COURSE_SLUG/forum/
    url(r'^$', views.summary, name='summary'),
    url(r'^'+POST_NUMBER+'$', views.view_thread, name='view_thread'),
    url(r'^'+POST_NUMBER+'/edit$', views.edit_post, name='edit_post'),
    url(r'^'+POST_NUMBER+'/pin', views.pin, name='pin'),
    url(r'^'+POST_NUMBER+'/lock', views.lock, name='lock'),
    url(r'^thread-list', views.thread_list, name='thread_list'),
    url(r'^new', views.new_thread, name='new_thread'),
    url(r'^'+POST_NUMBER+r'/react/(?P<reaction>\w+)$', views.react, name='react'),
    url(r'^identity', views.identity, name='identity'),
    url(r'^digest', views.digest, name='digest'),
    url(r'^search', views.search, name='search'),
    url(r'^dump', views.dump, name='dump'),
    url(r'^preview', views.preview, name='preview'),
]