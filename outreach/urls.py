from django.conf.urls import url
from outreach import views

outreach_pattern = [  # prefix /outreach/
    url('^$', views.index, name='index'),
    url(r'^new_event/$', views.new_event, name='new_event'),
    url(r'^(?P<event_id>\d+)/edit/$', views.edit_event, name='edit_event'),
    url(r'^(?P<event_id>\d+)/delete/$', views.delete_event, name='delete_event'),
    url(r'^(?P<event_id>\d+)/view/$', views.view_event, name='view_event'),

]
