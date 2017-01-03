from django.conf.urls import url
from courselib.urlparts import USERID_OR_EMPLID, SLUG_RE

REPORT_SLUG = '(?P<report>' + SLUG_RE + ')'
RUN_SLUG = '(?P<run>' + SLUG_RE + ')'
RESULT_SLUG = '(?P<result>' + SLUG_RE + ')'

report_patterns = [
    url(r'^$', 'reports.views.view_reports', name='view_reports'),
    url(r'^new$', 'reports.views.new_report', name='new_report'),
    url(r'^type/' + REPORT_SLUG + '$', 'reports.views.view_report', name='view_report'),
    url(r'^type/' + REPORT_SLUG + '/console', 'reports.views.console', name='console'),
    url(r'^type/' + REPORT_SLUG + '/access/new$', 'reports.views.new_access_rule', name='new_access_rule'),
    url(r'^type/' + REPORT_SLUG + '/access/delete/(?P<access_rule_id>\d+)$', 'reports.views.delete_access_rule', name='delete_access_rule'),
    url(r'^type/' + REPORT_SLUG + '/schedule/new$', 'reports.views.new_schedule_rule', name='new_schedule_rule'),
    url(r'^type/' + REPORT_SLUG + '/schedule/delete/(?P<schedule_rule_id>\d+)$', 'reports.views.delete_schedule_rule', name='delete_schedule_rule'),
    url(r'^type/' + REPORT_SLUG + '/component/new$', 'reports.views.new_component', name='new_component'),
    url(r'^type/' + REPORT_SLUG + '/component/delete/(?P<component_id>\d+)$', 'reports.views.delete_component', name='delete_component'),
    url(r'^type/' + REPORT_SLUG + '/query/new$', 'reports.views.new_query', name='new_query'),
    url(r'^type/' + REPORT_SLUG + '/query/edit/(?P<query_id>\d+)$', 'reports.views.edit_query', name='edit_query'),
    url(r'^type/' + REPORT_SLUG + '/query/delete/(?P<query_id>\d+)$', 'reports.views.delete_query', name='delete_query'),
    url(r'^type/' + REPORT_SLUG + '/run$', 'reports.views.run', name='run'),
    url(r'^type/' + REPORT_SLUG + '/run/' + RUN_SLUG + '$', 'reports.views.view_run', name='view_run'),
    url(r'^type/' + REPORT_SLUG + '/run/delete/' + RUN_SLUG + '$', 'reports.views.delete_run', name='delete_run'),
    url(r'^type/' + REPORT_SLUG + '/run/' + RUN_SLUG + '/' + RESULT_SLUG + "$", 'reports.views.view_result', name='view_result'),
    url(r'^type/' + REPORT_SLUG + '/run/' + RUN_SLUG + '/' + RESULT_SLUG + "/csv$", 'reports.views.csv_result', name='csv_result'),
]
