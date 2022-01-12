from django.urls import re_path as url
from courselib.urlparts import SLUG_RE
import visas.views as visas_views

ATTACH_SLUG = '(?P<attach_slug>' + SLUG_RE + ')'

visas_pattern = [ # prefix /visas/
    url(r'^$', visas_views.list_all_visas, name='list_all_visas'),
    url(r'^new_visa$', visas_views.new_visa, name='new_visa'),
    url(r'^download', visas_views.download_visas_csv, name='download_visas_csv'),
    url(r'^(?P<emplid>[\w\-]+)$', visas_views.list_all_visas, name='list_all_visas'),
    url(r'^new_visa/(?P<emplid>[\w\-]+)$', visas_views.new_visa, name='new_visa'),
    url(r'^(?P<visa_id>\d+)/edit_visa/$', visas_views.edit_visa, name='edit_visa'),
    url(r'^(?P<visa_id>\d+)/delete_visa/$', visas_views.delete_visa, name='delete_visa'),
    url(r'^(?P<visa_id>\d+)/new_attach', visas_views.new_attachment, name='new_attachment'),
    url(r'^(?P<visa_id>\d+)/view', visas_views.view_visa, name='view_visa'),
    url(r'^(?P<visa_id>\d+)/' + ATTACH_SLUG + '/delete$', visas_views.delete_attachment, name='delete_attachment'),
    url(r'^(?P<visa_id>\d+)/' + ATTACH_SLUG + '/view', visas_views.view_attachment, name='view_attachment'),
    url(r'^(?P<visa_id>\d+)/' + ATTACH_SLUG + '/download$', visas_views.download_attachment, name='download_attachment'),
]
