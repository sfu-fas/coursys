from django.conf.urls import patterns, url
from courselib.urlparts import USERID_OR_EMPLID, SLUG_RE

ALERT_TYPE_SLUG = '(?P<alert_type>' + SLUG_RE + ')'

alerts_patterns = [
    url(r'^new_alerts/$', alerts_views.rest_alerts, name='rest_alerts'),
    url(r'^$', alerts_views.view_alert_types, name='view_alert_types'),
    url(r'^send/' + ALERT_TYPE_SLUG + '/$', alerts_views.send_emails, name='send_emails'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/$', alerts_views.view_alerts, name='view_alerts'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/$', alerts_views.view_alert, name='view_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/resolved/$', alerts_views.view_resolved_alerts, name='view_resolved_alerts'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/all/$', alerts_views.view_all_alerts, name='view_all_alerts'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/delete$', alerts_views.hide_alert, name='hide_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/resolve', alerts_views.resolve_alert, name='resolve_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/reopen', alerts_views.reopen_alert, name='reopen_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/comment', alerts_views.comment_alert, name='comment_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/(?P<alert_id>\d+)/email', alerts_views.email_alert, name='email_alert'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/automation/$', alerts_views.view_automation, name='view_automation'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/automation/new/$', alerts_views.new_automation, name='new_automation'),
    url(r'^type/' + ALERT_TYPE_SLUG + '/automation/(?P<automation_id>\d+)/(?P<alert_id>\d+)/$', alerts_views.view_email_preview, name='view_email_preview' ),
    url(r'^type/' + ALERT_TYPE_SLUG + '/automation/(?P<automation_id>\d+)/delete/$', alerts_views.delete_automation, name='delete_automation' ),
]
