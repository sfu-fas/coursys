from django.conf.urls.defaults import patterns, url
from courselib.urlparts import USERID_OR_EMPLID, SLUG_RE

urlpatterns = patterns('',
    url(r'^$', 'reports.views.view_reports'),
)
