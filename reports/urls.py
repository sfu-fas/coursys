from django.conf.urls import patterns, url
from courselib.urlparts import USERID_OR_EMPLID, SLUG_RE

REPORT_SLUG = '(?P<report>' + SLUG_RE + ')'
RUN_SLUG = '(?P<run>' + SLUG_RE + ')'
RESULT_SLUG = '(?P<result>' + SLUG_RE + ')'

urlpatterns = patterns('',
    url(r'^$', 'reports.views.view_reports'),
    url(r'^new$', 'reports.views.new_report'),
    url(r'^type/' + REPORT_SLUG + '$', 'reports.views.view_report'),
    url(r'^type/' + REPORT_SLUG + '/console', 'reports.views.console'),
    url(r'^type/' + REPORT_SLUG + '/access/new$', 'reports.views.new_access_rule'),
    url(r'^type/' + REPORT_SLUG + '/access/delete/(?P<access_rule_id>\d+)$', 'reports.views.delete_access_rule'),
    url(r'^type/' + REPORT_SLUG + '/schedule/new$', 'reports.views.new_schedule_rule'),
    url(r'^type/' + REPORT_SLUG + '/schedule/delete/(?P<schedule_rule_id>\d+)$', 'reports.views.delete_schedule_rule'),
    url(r'^type/' + REPORT_SLUG + '/component/new$', 'reports.views.new_component'),
    url(r'^type/' + REPORT_SLUG + '/component/delete/(?P<component_id>\d+)$', 'reports.views.delete_component'),
    url(r'^type/' + REPORT_SLUG + '/alert/new$', 'reports.views.new_alert'),
    url(r'^type/' + REPORT_SLUG + '/query/new$', 'reports.views.new_query'),
    url(r'^type/' + REPORT_SLUG + '/query/edit/(?P<query_id>\d+)$', 'reports.views.edit_query'),
    url(r'^type/' + REPORT_SLUG + '/query/delete/(?P<query_id>\d+)$', 'reports.views.delete_query'),
    url(r'^type/' + REPORT_SLUG + '/run$', 'reports.views.run'),
    url(r'^type/' + REPORT_SLUG + '/run/' + RUN_SLUG + '$', 'reports.views.view_run'),
    url(r'^type/' + REPORT_SLUG + '/run/delete/' + RUN_SLUG + '$', 'reports.views.delete_run'),
    url(r'^type/' + REPORT_SLUG + '/run/' + RUN_SLUG + '/' + RESULT_SLUG + "$", 'reports.views.view_result'),
    url(r'^type/' + REPORT_SLUG + '/run/' + RUN_SLUG + '/' + RESULT_SLUG + "/csv$", 'reports.views.csv_result'),
)
