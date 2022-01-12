from django.urls import re_path as url
from outreach import views
from courselib.urlparts import ID_RE, SLUG_RE


EVENT_ID = '(?P<event_id>' + ID_RE + ')'
EVENT_SLUG = '(?P<event_slug>' + SLUG_RE + ')'
REGISTRATION_ID = '(?P<registration_id>' + ID_RE + ')'
PAST_FLAG = '(?P<past>' + ID_RE + ')'

outreach_pattern = [  # prefix /outreach/
    url('^$', views.outreach_index, name='outreach_index'),
    url(r'^new_event/$', views.new_event, name='new_event'),
    url(r'^' + EVENT_SLUG + '/edit$', views.edit_event, name='edit_event'),
    url(r'^' + EVENT_ID + '/delete$', views.delete_event, name='delete_event'),
    url(r'^' + EVENT_SLUG + '/view$', views.view_event, name='view_event'),
    url(r'^' + EVENT_SLUG + '/register$', views.register, name='register'),
    url(r'^' + EVENT_SLUG + '/registered$', views.register_success, name='register_success'),
    url(r'^' + EVENT_SLUG + '/waitlisted$', views.register_waitlisted, name='register_waitlisted'),
    url(r'^all_registrations/$', views.view_all_registrations, name='view_all_registrations'),
    url(r'^registration/' + REGISTRATION_ID + '/view$', views.view_registration, name='view_registration'),
    url(r'^registration/' + REGISTRATION_ID + '/edit$', views.edit_registration, name='edit_registration'),
    url(r'^registration/' + REGISTRATION_ID + '/edit/' + EVENT_SLUG + '/$', views.edit_registration,
        name='edit_registration'),
    url(r'^registration/' + REGISTRATION_ID + '/delete$', views.delete_registration, name='delete_registration'),
    url(r'^registration/' + REGISTRATION_ID + '/delete/' + EVENT_SLUG + '$', views.delete_registration,
        name='delete_registration'),
    url(r'^registration/' + REGISTRATION_ID + '/toggle$', views.toggle_registration_attendance,
        name='toggle_registration_attendance'),
    url(r'^registration/' + REGISTRATION_ID + '/toggle/' + EVENT_SLUG + '$', views.toggle_registration_attendance,
        name='toggle_registration_attendance'),
    url(r'^registration/' + REGISTRATION_ID + '/toggle_waitlist$', views.toggle_registration_waitlist,
        name='toggle_registration_waitlist'),
    url(r'^registration/' + REGISTRATION_ID + '/toggle_waitlist/' + EVENT_SLUG + '$', views.toggle_registration_waitlist,
        name='toggle_registration_waitlist'),
    url(r'^' + EVENT_SLUG + '/registrations$', views.view_event_registrations, name='view_event_registrations'),
    url(r'^download_events$', views.download_current_events_csv, name='download_events'),
    url(r'^download_events/' + PAST_FLAG + '$', views.download_current_events_csv, name='download_events'),
    url(r'^' + EVENT_SLUG + 'download_registrations/$', views.download_registrations, name='download_registrations'),
    url(r'^download_registrations$', views.download_registrations, name='download_registrations'),
    url(r'^download_registrations/' + PAST_FLAG + '$', views.download_registrations, name='download_registrations'),
]
