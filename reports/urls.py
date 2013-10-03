from django.conf.urls.defaults import patterns, url
from courselib.urlparts import USERID_OR_EMPLID, SLUG_RE

REPORT_SLUG = '(?P<report>' + SLUG_RE + ')'

urlpatterns = patterns('',
    url(r'^$', 'reports.views.view_reports'),
    url(r'^new$', 'reports.views.new_report'),
    url(r'^type/' + REPORT_SLUG + '$', 'reports.views.view_report'),
    url(r'^type/' + REPORT_SLUG + '/component/new$', 'reports.views.new_component'),
    url(r'^type/' + REPORT_SLUG + '/component/delete/(?P<component_id>\d+)$', 'reports.views.delete_component'),
    url(r'^type/' + REPORT_SLUG + '/run$', 'reports.views.run'),
)
