from django.conf.urls import url
from courselib.urlparts import SLUG_RE, ID_RE
import relationships.views as rel_views

CONTACT_SLUG = '(?P<contact_slug>' + SLUG_RE + ')'
EVENT_SLUG = '(?P<event_slug>' + SLUG_RE + ')'
HANDLER_SLUG = '(?P<handler_slug>' + SLUG_RE + ')'


relationship_patterns = [ # prefix /relationships/
    url(r'^$', rel_views.index, name='index'),
    url(r'^download_contacts_csv$', rel_views.download_contacts_csv, name='download_contacts'),
    url(r'^new_contact$', rel_views.new_contact, name='new_contact'),
    url(r'^' + CONTACT_SLUG + '/view', rel_views.view_contact, name='view_contact'),
    url(r'^' + CONTACT_SLUG + '/edit$', rel_views.edit_contact, name='edit_contact'),
    url(r'^' + CONTACT_SLUG + '/delete$', rel_views.delete_contact, name='delete_contact'),
    url(r'^' + CONTACT_SLUG + '/list_events', rel_views.list_events, name='list_events'),
    url(r'^' + CONTACT_SLUG + '/add_event/' + HANDLER_SLUG, rel_views.add_event, name='add_event'),
    url(r'^' + CONTACT_SLUG + '/' + EVENT_SLUG + '/view/', rel_views.view_event, name='view_event'),
    url(r'^' + CONTACT_SLUG + '/' + EVENT_SLUG + '/delete/', rel_views.delete_event, name='delete_event'),
    url(r'^' + CONTACT_SLUG + '/' + EVENT_SLUG + '/edit/', rel_views.edit_event, name='edit_event'),
    url(r'^list_reports$', rel_views.list_reports, name='list_reports'),
    url(r'^' + HANDLER_SLUG + '/report/', rel_views.event_report, name='event_report'),
    url(r'^' + HANDLER_SLUG + '/report_csv/', rel_views.event_report_download, name='event_report_download'),
]
