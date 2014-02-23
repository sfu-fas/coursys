from django.conf.urls import patterns, url
from courselib.urlparts import USERID_OR_EMPLID, SLUG_RE

ALERT_TYPE_SLUG = '(?P<alert_type>' + SLUG_RE + ')'

urlpatterns = patterns('',
    url(r'^new_alerts/$', 'alerts.views.rest_alerts'),
    url(r'^$', 'alerts.views.view_alert_types'),
    url(r'^send/' + ALERT_TYPE_SLUG + '/$', 'alerts.views.send_emails'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/$', 'alerts.views.view_alerts'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/$', 'alerts.views.view_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/resolved/$', 'alerts.views.view_resolved_alerts'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/all/$', 'alerts.views.view_all_alerts'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/delete$', 'alerts.views.hide_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/resolve', 'alerts.views.resolve_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/reopen', 'alerts.views.reopen_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/comment', 'alerts.views.comment_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/email', 'alerts.views.email_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/automation/$', 'alerts.views.view_automation'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/automation/new/$', 'alerts.views.new_automation'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/automation/(?P<automation_id>\d+)/(?P<alert_id>\d+)/$', 'alerts.views.view_email_preview' ),    
    url(r'^type/' + ALERT_TYPE_SLUG + '/automation/(?P<automation_id>\d+)/delete/$', 'alerts.views.delete_automation' ),    
)
