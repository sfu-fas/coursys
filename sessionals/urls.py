from django.conf.urls import url
from sessionals import views
from courselib.urlparts import SLUG_RE

sessionals_patterns = [ # prefix /sessionals/
    url(r'^$', views.index, name='index'),
    url(r'^manage_accounts/$', views.manage_accounts, name='manage_accounts'),
    url(r'^new_account/$', views.new_account, name='new_account'),
    ]
