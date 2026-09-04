from django.urls import re_path as url
from courselib.urlparts import USERID_OR_EMPLID
from postdoc import views

postdoc_patterns = [  # prefix /postdoc/
    url(r'^$', views.post_doctoral_fellow, name='post_doctoral_fellow'),
    url(r'^download_index/$', views.download_index, name='download_index'),
    url(r'^download_admin/$', views.download_admin, name='download_admin'),
    url(r'^new/$', views.new_postdoc_appointment, name='new_postdoc_appointment'),
    url(r'^(?P<postdoc_slug>[\w-]+)/$', views.view_postdoc_appointment, name='view_postdoc_appointment'),
    url(r'^(?P<postdoc_slug>[\w-]+)/edit/$', views.edit_postdoc_appointment, name='edit_postdoc_appointment'),
    url(r'^(?P<postdoc_slug>[\w-]+)/delete/$', views.delete_postdoc_appointment, name='delete_postdoc_appointment'),
    url(r'^(?P<postdoc_slug>[\w-]+)/edit_notes/$', views.edit_postdoc_notes, name='edit_postdoc_notes'),
    url(r'^(?P<postdoc_slug>[\w-]+)/new_attachment/$', views.new_admin_attachment, name='new_admin_attachment'),
    url(r'^(?P<postdoc_slug>[\w-]+)/attachment/(?P<attach_slug>[\w-]+)/view/$', views.view_admin_attachment, name='view_admin_attachment'),
    url(r'^(?P<postdoc_slug>[\w-]+)/attachment/(?P<attach_slug>[\w-]+)/download/$', views.download_admin_attachment, name='download_admin_attachment'),
    url(r'^(?P<postdoc_slug>[\w-]+)/attachment/(?P<attach_slug>[\w-]+)/delete/$', views.delete_admin_attachment, name='delete_admin_attachment'),
    url(r'^advanced_search/appointee_appointments/' + USERID_OR_EMPLID + '/$', views.appointee_appointments, name='appointee_appointments'),
    url(r'^advanced_search/supervisor_appointments/' + USERID_OR_EMPLID + '/$', views.supervisor_appointments, name='supervisor_appointments'),
]
