from django.conf.urls import url, include
from django.conf import settings
from django.views.generic import TemplateView,  RedirectView

from courselib.urlparts import USERID_SLUG, COURSE_SLUG

from advisornotes.urls import advisornotes_patterns
from coredata.urls import data_patterns, admin_patterns, sysadmin_patterns, browse_patterns
from dashboard.urls import config_patterns, news_patterns, calendar_patterns, docs_patterns, studentsearch_patterns
from discipline.urls import discipline_patterns
from faculty.urls import faculty_patterns
from onlineforms.urls import forms_patterns
from grad.urls import grad_patterns
from grades.urls import offering_patterns
from ra.urls import ra_patterns
from reports.urls import report_patterns
from ta.urls import ta_patterns, tug_patterns
from tacontracts.urls import tacontract_patterns
from visas.urls import visas_pattern
from outreach.urls import outreach_pattern
from sessionals.urls import sessionals_patterns
from inventory.urls import inventory_pattern
from relationships.urls import relationship_patterns
from api.urls import api_patterns
from otp.urls import otp_patterns

import dashboard.views as dashboard_views
import grad.views as grad_views
from django_cas.views import logout

handler404 = 'courselib.auth.NotFoundResponse'

toplevel_patterns = [
    # system URLs
    url(r'^login/$', dashboard_views.login, name='login'),
    url(r'^logout/$', logout, {'next_page': '/'}, name='logout'),
    url(r'^logout/(?P<next_page>.*)/$', logout, name='auth_logout_next'),
    url(r'^robots.txt$', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    url(r'^favicon.ico$', RedirectView.as_view(url=settings.STATIC_URL + 'icons/favicon.ico', permanent=True)),

    # top-level pages
    url(r'^$', dashboard_views.index, name='index'),
    url(r'^history$', dashboard_views.index_full, name='index_full'),
    url(r'^search$', dashboard_views.site_search, name='site_search'),

    url(r'^my_grads/$', grad_views.supervisor_index, name='supervisor_index'),
    url(r'^my_grads/download/$', grad_views.download_my_grads_csv, name='download_my_grads_csv'),
]

urlpatterns = [
    url(r'', include(toplevel_patterns, namespace='dashboard')),

    # top-level paths from dashboard and coredata
    url(r'^api/', include(api_patterns, namespace='api')),
    url(r'^admin/', include(admin_patterns, namespace='admin')),
    url(r'^browse/', include(browse_patterns, namespace='browse')),
    url(r'^calendar/', include(calendar_patterns, namespace='calendar')),
    url(r'^config/', include(config_patterns, namespace='config')),
    url(r'^data/', include(data_patterns, namespace='data')),
    url(r'^docs/', include(docs_patterns, namespace='docs')),
    url(r'^news/', include(news_patterns, namespace='news')),
    url(r'^students/', include(studentsearch_patterns, namespace='students')),
    url(r'^sysadmin/', include(sysadmin_patterns, namespace='sysadmin')),
    url(r'^2fa/', include(otp_patterns, namespace='otp')),

    # course offering URL hierarchy: many apps sub-included there
    # among them: discipline, discuss, groups, marking, pages, submission
    url(r'^' + COURSE_SLUG + '/', include(offering_patterns, namespace='offering')),

    # nicely self-contained apps
    url(r'^advising/', include(advisornotes_patterns, namespace='advising')),
    url(r'^discipline/', include(discipline_patterns, namespace='discipline')),
    url(r'^faculty/', include(faculty_patterns, namespace='faculty')),
    url(r'^forms/', include(forms_patterns, namespace='onlineforms')),
    url(r'^reports/', include(report_patterns, namespace='reports')),
    url(r'^relationships/', include(relationship_patterns, namespace='relationships')),

    # graduate student-related apps
    url(r'^grad/', include(grad_patterns, namespace='grad')),
    url(r'^ra/', include(ra_patterns, namespace='ra')),
    url(r'^ta/', include(ta_patterns, namespace='ta')),
    url(r'^tacontracts/', include(tacontract_patterns, namespace='tacontracts')),
    url(r'^tugs/', include(tug_patterns, namespace='tugs')),
    url(r'^visas/', include(visas_pattern, namespace='visas')),
    url(r'^outreach/', include(outreach_pattern, namespace='outreach')),
    url(r'^sessionals/', include(sessionals_patterns, namespace='sessionals')),
    url(r'^inventory/', include(inventory_pattern, namespace='inventory')),

    # redirect old mobile URLs to rightful locations
    url(r'^m/(?P<urltail>.*)$',  RedirectView.as_view(url='/%(urltail)s/', permanent=True)),
    # accept the URL provided by User.get_absolute_url
    url(r'^users/' + USERID_SLUG + '/$', RedirectView.as_view(url='/sysadmin/users/%(userid)s/', permanent=True)),
]

if settings.DEPLOY_MODE != 'production':
    # URLs for development only:
    urlpatterns += [
        url(r'^fake_login', dashboard_views.fake_login, name='fake_login'),
        url(r'^fake_logout', dashboard_views.fake_logout, name='fake_logout'),
    ]

if settings.DEBUG_TOOLBAR:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]