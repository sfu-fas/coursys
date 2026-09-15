from django.urls import re_path as url

from system import views

system_patterns = [
    url(r'^$', views.list_systemvariables, name='list_systemvariables'),
    url(r'^new/$', views.new_systemvariable, name='new_systemvariable'),
    url(r'^(?P<systemvariable_id>\d+)/edit/$', views.edit_systemvariable, name='edit_systemvariable'),
    url(r'^(?P<systemvariable_id>\d+)/delete/$', views.delete_systemvariable, name='delete_systemvariable'),
]
