from django.urls import re_path as url
from sessionals import views
from courselib.urlparts import SLUG_RE, ID_RE


ACCOUNT_ID = '(?P<account_id>' + ID_RE + ')'
ACCOUNT_SLUG = '(?P<account_slug>' + SLUG_RE + ')'
CONFIG_SLUG = '(?P<config_slug>' + SLUG_RE + ')'
CONTRACT_ID = '(?P<contract_id>' + ID_RE + ')'
CONTRACT_SLUG = '(?P<contract_slug>' + SLUG_RE + ')'
ATTACH_SLUG = '(?P<attach_slug>' + SLUG_RE + ')'


sessionals_patterns = [ # prefix /sessionals/
    url(r'^$', views.sessionals_index, name='sessionals_index'),
    url(r'^download/$', views.download_sessionals, name='download_sessionals'),
    url(r'^manage_accounts/$', views.manage_accounts, name='manage_accounts'),
    url(r'^new_account/$', views.new_account, name='new_account'),
    url(r'^' + ACCOUNT_SLUG + '/edit$', views.edit_account, name='edit_account'),
    url(r'^' + ACCOUNT_ID + '/delete$', views.delete_account, name='delete_account'),
    url(r'^' + ACCOUNT_SLUG + '/view$', views.view_account, name='view_account'),
    url(r'^manage_configs/$', views.manage_configs, name='manage_configs'),
    url(r'^new_config/$', views.new_config, name='new_config'),
    url(r'^config/' + CONFIG_SLUG + '/edit$', views.edit_config, name='edit_config'),
    url(r'^new_contract/$', views.new_contract, name='new_contract'),
    url(r'^contract/' + CONTRACT_SLUG + '/edit$', views.edit_contract, name='edit_contract'),
    url(r'^contract/' + CONTRACT_ID + '/delete$', views.delete_contract, name='delete_contract'),
    url(r'^contract/' + CONTRACT_SLUG + '/print$', views.print_contract, name='print_form'),
    url(r'^contract/' + CONTRACT_SLUG + '/view$', views.view_contract, name='view_contract'),
    url(r'^contract/' + CONTRACT_SLUG + '/new_attach$', views.new_attachment, name='new_attachment'),
    url(r'^contract/' + CONTRACT_SLUG + '/attach/' + ATTACH_SLUG + '/delete$', views.delete_attachment,
        name='delete_attachment'),
    url(r'^contract/' + CONTRACT_SLUG + '/attach/' + ATTACH_SLUG + '/view', views.view_attachment, name='view_attachment'),
    url(r'^contract/' + CONTRACT_SLUG + '/attach/' + ATTACH_SLUG + '/download$', views.download_attachment,
        name='download_attachment'),
    ]
