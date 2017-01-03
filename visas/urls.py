from django.conf.urls import url
from courselib.urlparts import SLUG_RE

ATTACH_SLUG = '(?P<attach_slug>' + SLUG_RE + ')'

visas_pattern = [ # prefix /visas/
    url(r'^$', 'visas.views.list_all_visas', name='list_all_visas'),
    url(r'^new_visa$', 'visas.views.new_visa', name='new_visa'),
    url(r'^download', 'visas.views.download_visas_csv', name='download_visas_csv'),
    url(r'^(?P<emplid>[\w\-]+)$', 'visas.views.list_all_visas', name='list_all_visas'),
    url(r'^new_visa/(?P<emplid>[\w\-]+)$', 'visas.views.new_visa', name='new_visa'),
    url(r'^(?P<visa_id>\d+)/edit_visa/$', 'visas.views.edit_visa', name='edit_visa'),
    url(r'^(?P<visa_id>\d+)/delete_visa/$', 'visas.views.delete_visa', name='delete_visa'),
    url(r'^(?P<visa_id>\d+)/new_attach', 'visas.views.new_attachment', name='new_attachment'),
    url(r'^(?P<visa_id>\d+)/view', 'visas.views.view_visa', name='view_visa'),
    url(r'^(?P<visa_id>\d+)/' + ATTACH_SLUG + '/delete$', 'visas.views.delete_attachment', name='delete_attachment'),
    url(r'^(?P<visa_id>\d+)/' + ATTACH_SLUG + '/view', 'visas.views.view_attachment', name='view_attachment'),
    url(r'^(?P<visa_id>\d+)/' + ATTACH_SLUG + '/download$', 'visas.views.download_attachment', name='download_attachment'),
]
