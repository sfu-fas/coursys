from django.conf.urls import url

from courselib.urlparts import USERID_OR_EMPLID
from . import views

forum_patterns = [ # prefix /COURSE_SLUG/forum/
    url(r'^$', views.index, name='index'),
    url(r'^new', views.new_thread, name='new_thread'),
]