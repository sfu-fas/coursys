from django.conf.urls import url
from inventory import views
from courselib.urlparts import ID_RE, SLUG_RE

ASSET_SLUG = '(?P<asset_slug>' + SLUG_RE + ')'
ASSET_ID = '(?P<asset_id>' + ID_RE + ')'

inventory_pattern = [  # prefix /inventory/
    url('^$', views.index, name='index'),
    url(r'^new_asset/$', views.new_asset, name='new_asset'),
    url(r'^' + ASSET_SLUG + '/edit$', views.edit_asset, name='edit_asset'),
    url(r'^' + ASSET_ID + '/delete$', views.delete_asset, name='delete_asset'),
    url(r'^' + ASSET_SLUG + '/view$', views.view_asset, name='view_asset'),
]
