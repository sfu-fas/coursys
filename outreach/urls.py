from django.conf.urls import url
from outreach import views
from courselib.urlparts import ID_RE, SLUG_RE


EVENT_ID = '(?P<event_id>' + ID_RE + ')'
#EVENT_SLUG = '(?P<event_slug>' + SLUG_RE + ')'
EVENT_SLUG = '(?P<event_slug>[\w\-\.]+)'

outreach_pattern = [  # prefix /outreach/
    url('^$', views.index, name='index'),
    url(r'^new_event/$', views.new_event, name='new_event'),
    url(r'^' + EVENT_SLUG + '/edit$', views.edit_event, name='edit_event'),
    url(r'^' + EVENT_ID + '/delete$', views.delete_event, name='delete_event'),
    url(r'^' + EVENT_SLUG + '/view$', views.view_event, name='view_event'),
    url(r'^' + EVENT_SLUG + '/register$', views.register, name='register'),
    url(r'^' + EVENT_SLUG + '/registered$', views.register_success, name='register_success'),
]
