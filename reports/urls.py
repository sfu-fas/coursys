from django.urls import re_path as url
from courselib.urlparts import SLUG_RE
import reports.views as reports_views

REPORT_SLUG = '(?P<report>' + SLUG_RE + ')'
RUN_SLUG = '(?P<run>' + SLUG_RE + ')'
RESULT_SLUG = '(?P<result>' + SLUG_RE + ')'

report_patterns = [
    url(r'^$', reports_views.view_reports, name='view_reports'),
    url(r'^new$', reports_views.new_report, name='new_report'),
    url(r'^type/' + REPORT_SLUG + '$', reports_views.view_report, name='view_report'),
    url(r'^type/' + REPORT_SLUG + '/edit$', reports_views.edit_report, name='edit_report'),
    url(r'^type/' + REPORT_SLUG + '/console', reports_views.console, name='console'),
    url(r'^type/' + REPORT_SLUG + '/access/new$', reports_views.new_access_rule, name='new_access_rule'),
    url(r'^type/' + REPORT_SLUG + r'/access/delete/(?P<access_rule_id>\d+)$', reports_views.delete_access_rule, name='delete_access_rule'),
    url(r'^type/' + REPORT_SLUG + '/schedule/new$', reports_views.new_schedule_rule, name='new_schedule_rule'),
    url(r'^type/' + REPORT_SLUG + r'/schedule/delete/(?P<schedule_rule_id>\d+)$', reports_views.delete_schedule_rule, name='delete_schedule_rule'),
    url(r'^type/' + REPORT_SLUG + '/component/new$', reports_views.new_component, name='new_component'),
    url(r'^type/' + REPORT_SLUG + r'/component/delete/(?P<component_id>\d+)$', reports_views.delete_component, name='delete_component'),
    url(r'^type/' + REPORT_SLUG + '/query/new$', reports_views.new_query, name='new_query'),
    url(r'^type/' + REPORT_SLUG + r'/query/edit/(?P<query_id>\d+)$', reports_views.edit_query, name='edit_query'),
    url(r'^type/' + REPORT_SLUG + r'/query/delete/(?P<query_id>\d+)$', reports_views.delete_query, name='delete_query'),
    url(r'^type/' + REPORT_SLUG + '/run$', reports_views.run, name='run'),
    url(r'^type/' + REPORT_SLUG + '/run/' + RUN_SLUG + '$', reports_views.view_run, name='view_run'),
    url(r'^type/' + REPORT_SLUG + '/run/delete/' + RUN_SLUG + '$', reports_views.delete_run, name='delete_run'),
    url(r'^type/' + REPORT_SLUG + '/run/' + RUN_SLUG + '/' + RESULT_SLUG + "$", reports_views.view_result, name='view_result'),
    url(r'^type/' + REPORT_SLUG + '/run/' + RUN_SLUG + '/' + RESULT_SLUG + "/csv$", reports_views.csv_result, name='csv_result'),
]
