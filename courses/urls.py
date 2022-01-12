from django.urls import include, re_path as url
from django.conf import settings
from django.views.generic import TemplateView,  RedirectView

from courselib.urlparts import USERID_SLUG, COURSE_SLUG
from courselib.csp import csp_report_view

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
from space.urls import space_patterns
from reminders.urls import reminders_patterns

import dashboard.views as dashboard_views
import grad.views as grad_views
from django_cas_ng.views import LogoutView
from submission.views import moss_icon

handler404 = 'courselib.auth.NotFoundResponse'

toplevel_patterns = [
    # system URLs
    url(r'^login/$', dashboard_views.LoginView.as_view(), name='login'),
    url(r'^logout/$', LogoutView.as_view(), name='logout'),
    url(r'^robots.txt$', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    url(r'^favicon.ico$', RedirectView.as_view(url=settings.STATIC_URL + 'icons/favicon.ico', permanent=True)),
    url(r'^csp-reports', csp_report_view, name='csp_reports'),
    url(r'^mossicon/(?P<filename>.*)$', moss_icon, name='moss_icon'),
    url(r'^frontend-check$', dashboard_views.frontend_check, name='frontend_check'),

    # top-level pages
    url(r'^$', dashboard_views.index, name='index'),
    url(r'^history$', dashboard_views.index_full, name='index_full'),
    url(r'^search$', dashboard_views.site_search, name='site_search'),

    url(r'^my_grads/$', grad_views.supervisor_index, name='supervisor_index'),
    url(r'^my_grads/download/$', grad_views.download_my_grads_csv, name='download_my_grads_csv'),
]

urlpatterns = [
    url(r'', include((toplevel_patterns, 'dashboard'), namespace='dashboard')),

    # top-level paths from dashboard and coredata
    url(r'^admin/', include((admin_patterns, 'admin'), namespace='admin')),
    url(r'^browse/', include((browse_patterns, 'browse'), namespace='browse')),
    url(r'^calendar/', include((calendar_patterns, 'calendar'), namespace='calendar')),
    url(r'^config/', include((config_patterns, 'config'), namespace='config')),
    url(r'^data/', include((data_patterns, 'data'), namespace='data')),
    url(r'^docs/', include((docs_patterns, 'docs'), namespace='docs')),
    url(r'^news/', include((news_patterns, 'news'), namespace='news')),
    url(r'^students/', include((studentsearch_patterns, 'students'), namespace='students')),
    url(r'^sysadmin/', include((sysadmin_patterns, 'sysadmin'), namespace='sysadmin')),

    # course offering URL hierarchy: many apps sub-included there
    # among them: discipline, discuss, groups, marking, pages, submission
    url(r'^' + COURSE_SLUG + '/', include((offering_patterns, 'grades'), namespace='offering')),

    # nicely self-contained apps
    url(r'^advising/', include((advisornotes_patterns, 'advisornotes'), namespace='advising')),
    url(r'^discipline/', include((discipline_patterns, 'discipline'), namespace='discipline')),
    url(r'^faculty/', include((faculty_patterns, 'faculty'), namespace='faculty')),
    url(r'^forms/', include((forms_patterns, 'onlineforms'), namespace='onlineforms')),
    url(r'^reports/', include((report_patterns, 'reports'), namespace='reports')),
    url(r'^relationships/', include((relationship_patterns, 'relationships'), namespace='relationships')),
    url(r'^visas/', include((visas_pattern, 'visas'), namespace='visas')),
    url(r'^outreach/', include((outreach_pattern, 'outreach'), namespace='outreach')),
    url(r'^sessionals/', include((sessionals_patterns, 'sessionals'), namespace='sessionals')),
    url(r'^inventory/', include((inventory_pattern, 'inventory'), namespace='inventory')),
    url(r'^space/', include((space_patterns, 'space'), namespace='space')),
    url(r'^reminders/', include((reminders_patterns, 'reminders'), namespace='reminders')),


    # graduate student-related apps
    url(r'^grad/', include((grad_patterns, 'grad'), namespace='grad')),
    url(r'^ra/', include((ra_patterns, 'ra'), namespace='ra')),
    url(r'^ta/', include((ta_patterns, 'ta'), namespace='ta')),
    url(r'^tacontracts/', include((tacontract_patterns, 'tacontracts'), namespace='tacontracts')),
    url(r'^tugs/', include((tug_patterns, 'tugs'), namespace='tugs')),


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