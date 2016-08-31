from django.conf.urls import url
from inventory import views
from courselib.urlparts import ID_RE, SLUG_RE

ASSET_SLUG = '(?P<asset_slug>' + SLUG_RE + ')'
ASSET_ID = '(?P<asset_id>' + ID_RE + ')'
ATTACH_SLUG = '(?P<attach_slug>' + SLUG_RE + ')'
CHANGE_RECORD_ID = '(?P<record_id>' + ID_RE + ')'


inventory_pattern = [  # prefix /inventory/
    url('^$', views.inventory_index, name='inventory_index'),
    url(r'^new_asset/$', views.new_asset, name='new_asset'),
    url(r'^' + ASSET_SLUG + '/edit$', views.edit_asset, name='edit_asset'),
    url(r'^' + ASSET_ID + '/delete$', views.delete_asset, name='delete_asset'),
    url(r'^' + ASSET_SLUG + '/view$', views.view_asset, name='view_asset'),
    url(r'^' + ASSET_SLUG + '/add_change', views.add_change_record, name='add_change_record'),
    url(r'^' + ASSET_ID + '/new_attach$', views.new_attachment, name='new_attachment'),
    url(r'^' + ASSET_ID + '/attach/' + ATTACH_SLUG + '/delete$', views.delete_attachment,
        name='delete_attachment'),
    url(r'^' + ASSET_ID + '/attach/' + ATTACH_SLUG + '/view', views.view_attachment, name='view_attachment'),
    url(r'^' + ASSET_ID + '/attach/' + ATTACH_SLUG + '/download$', views.download_attachment,
        name='download_attachment'),
    url(r'^' + CHANGE_RECORD_ID + '/delete_record$', views.delete_change_record, name='delete_change_record'),

]
