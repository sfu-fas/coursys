from django.conf.urls import url


visas_pattern = [ # prefix /visas/
    url(r'^$', 'visas.views.list_all_visas'),
    url(r'^download', 'visas.views.download_visas_csv'),
    url(r'^new_visa$', 'visas.views.new_visa'),
    url(r'^(?P<visa_id>\d+)/edit_visa/$', 'visas.views.edit_visa'),
    url(r'^(?P<visa_id>\d+)/delete_visa/$', 'visas.views.delete_visa'),
]
