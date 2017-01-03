from django.conf.urls import patterns, url
from courselib.urlparts import USERID_OR_EMPLID, SLUG_RE

ALERT_TYPE_SLUG = '(?P<alert_type>' + SLUG_RE + ')'

alerts_patterns = [
    url(r'^new_alerts/$', 'alerts.views.rest_alerts', name='rest_alerts'),
    url(r'^$', 'alerts.views.view_alert_types', name='view_alert_types'),
    url(r'^send/' + ALERT_TYPE_SLUG + '/$', 'alerts.views.send_emails', name='send_emails'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/$', 'alerts.views.view_alerts', name='view_alerts'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/$', 'alerts.views.view_alert', name='view_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/resolved/$', 'alerts.views.view_resolved_alerts', name='view_resolved_alerts'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/all/$', 'alerts.views.view_all_alerts', name='view_all_alerts'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/delete$', 'alerts.views.hide_alert', name='hide_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/resolve', 'alerts.views.resolve_alert', name='resolve_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/reopen', 'alerts.views.reopen_alert', name='reopen_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/comment', 'alerts.views.comment_alert', name='comment_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/email', 'alerts.views.email_alert', name='email_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/automation/$', 'alerts.views.view_automation', name='view_automation'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/automation/new/$', 'alerts.views.new_automation', name='new_automation'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/automation/(?P<automation_id>\d+)/(?P<alert_id>\d+)/$', 'alerts.views.view_email_preview', name='view_email_preview' ),
    url(r'^type/' + ALERT_TYPE_SLUG + '/automation/(?P<automation_id>\d+)/delete/$', 'alerts.views.delete_automation', name='delete_automation' ),
]
