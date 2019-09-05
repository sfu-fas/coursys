from django.conf.urls import url
from courselib.urlparts import SLUG_RE, ID_RE
from space import views


LOCATION_SLUG = '(?P<location_slug>' + SLUG_RE + ')'
BOOKING_SLUG = '(?P<booking_slug>' + SLUG_RE + ')'
LOCATION_ID = '(?P<location_id>' + ID_RE + ')'
ROOMTYPE_SLUG = '(?P<roomtype_slug>' + SLUG_RE + ')'
BOOKING_ID = '(?P<booking_id>' + ID_RE + ')'
ROOMTYPE_ID = '(?P<roomtype_id>' + ID_RE + ')'
FROM_INDEX = '(?P<from_index>' + ID_RE + ')'
ATTACHMENT_ID = '(?P<attachment_id>' + ID_RE + ')'
SAFETY_ITEM_SLUG = '(?P<safety_item_slug>' + SLUG_RE + ')'


space_patterns = [  # prefix /space/
    url('^$', views.index, name='index'),
    url('^download/$', views.download_locations, name='download_locations'),
    url(r'^new_location/$', views.add_location, name='add_location'),
    url(r'^' + LOCATION_SLUG + '/edit$', views.edit_location, name='edit_location'),
    url(r'^' + LOCATION_SLUG + '/edit/' + FROM_INDEX + '/$', views.edit_location, name='edit_location'),
    url(r'^' + LOCATION_SLUG + '/view$', views.view_location, name='view_location'),
    url(r'^' + LOCATION_ID + '/delete$', views.delete_location, name='delete_location'),
    url(r'^roomtypes/$', views.list_roomtypes, name='list_roomtypes'),
    url(r'^new_roomtype/$', views.add_roomtype, name='add_roomtype'),
    url(r'^roomtypes/' + ROOMTYPE_SLUG + '/edit$', views.edit_roomtype, name='edit_roomtype'),
    url(r'^roomtypes/' + ROOMTYPE_SLUG + '/view$', views.view_roomtype, name='view_roomtype'),
    url(r'^roomtypes/' + ROOMTYPE_ID + '/delete$', views.delete_roomtype, name='delete_roomtype'),
    url(r'^' + LOCATION_SLUG + '/add_booking$', views.add_booking, name='add_booking'),
    url(r'^' + LOCATION_SLUG + '/add_booking/' + FROM_INDEX + '/$', views.add_booking, name='add_booking'),
    url(r'^bookings/' + BOOKING_SLUG + '/keyform$', views.keyform, name='keyform'),
    url(r'^bookings/' + BOOKING_SLUG + '/delete_key$', views.delete_key, name='delete_key'),
    url(r'^bookings/' + BOOKING_SLUG + '/edit$', views.edit_booking, name='edit_booking'),
    url(r'^bookings/' + BOOKING_SLUG + '/view$', views.view_booking, name='view_booking'),
    url(r'^bookings/' + BOOKING_ID + '/delete$', views.delete_booking, name='delete_booking'),
    url(r'^bookings/' + BOOKING_SLUG + '/attach$', views.add_booking_attachment, name='add_booking_attachment'),
    url(r'^bookings/' + BOOKING_SLUG + '/attachment/' + ATTACHMENT_ID + '/view$', views.view_booking_attachment,
        name='view_booking_attachment'),
    url(r'^bookings/' + BOOKING_SLUG + '/attachment/' + ATTACHMENT_ID + '/download', views.download_booking_attachment,
        name='download_booking_attachment'),
    url(r'^bookings/' + BOOKING_SLUG + '/attachment/' + ATTACHMENT_ID + '/delete$', views.delete_booking_attachment,
        name='delete_booking_attachment'),
    url(r'^bookings/' + BOOKING_SLUG + '/send_memo$', views.send_memo, name='send_booking_memo'),
    url(r'^bookings/' + BOOKING_SLUG + '/send_memo/' + FROM_INDEX + '/$', views.send_memo, name='send_booking_memo'),
    url(r'safety_items/$', views.manage_room_safety_items, name='manage_safety_items'),
    url(r'new_safety_item/$', views.add_room_safety_item, name='add_safety_item'),
    url(r'safety_items/' + SAFETY_ITEM_SLUG + '/edit$', views.edit_room_safety_item, name='edit_safety_item'),
    url(r'safety_items/' + SAFETY_ITEM_SLUG + '/delete$', views.delete_room_safety_item, name='delete_safety_item'),
]
