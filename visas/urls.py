from django.conf.urls import url


visas_pattern = [ # prefix /visas/
    url(r'^$', 'visas.views.list_all_visas'),
    url(r'^new_visa$', 'visas.views.new_visa'),
]