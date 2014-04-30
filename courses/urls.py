from django.conf.urls import url, include
from django.conf import settings
from django.views.generic import TemplateView,  RedirectView

from courselib.urlparts import USERID_SLUG, COURSE_SLUG

from advisornotes.urls import advisornotes_patterns
from alerts.urls import alerts_patterns
from coredata.urls import data_patterns, admin_patterns, sysadmin_patterns, browse_patterns
from dashboard.urls import config_patterns, news_patterns, calendar_patterns, docs_patterns, studentsearch_patterns
from discipline.urls import discipline_patterns
from faculty.urls import faculty_patterns
from onlineforms.urls import forms_patterns
from gpaconvert.urls import gpaconvert_patterns
from grad.urls import grad_patterns
from grades.urls import offering_patterns
from ra.urls import ra_patterns
from reports.urls import report_patterns
from ta.urls import ta_patterns, tug_patterns

handler404 = 'courselib.auth.NotFoundResponse'

urlpatterns = [
    # system URLs
    url(r'^login/$', 'dashboard.views.login'),
    url(r'^logout/$', 'django_cas.views.logout', {'next_page': '/'}),
    url(r'^logout/(?P<next_page>.*)/$', 'django_cas.views.logout', name='auth_logout_next'),
    url(r'^robots.txt$', TemplateView.as_view(template_name='robots.txt', content_type='text/plain')),
    url(r'^favicon.ico$', RedirectView.as_view(url=settings.STATIC_URL+'icons/favicon.ico', permanent=True)),

    # top-level pages
    url(r'^$', 'dashboard.views.index'),
    url(r'^history$', 'dashboard.views.index_full'),
    url(r'^search$', 'dashboard.views.site_search'),

    # top-level paths from dashboard and coredata
    url(r'^admin/', include(admin_patterns)),
    url(r'^browse/', include(browse_patterns)),
    url(r'^calendar/', include(calendar_patterns)),
    url(r'^config/', include(config_patterns)),
    url(r'^data/', include(data_patterns)),
    url(r'^docs/', include(docs_patterns)),
    url(r'^news/', include(news_patterns)),
    url(r'^students/', include(studentsearch_patterns)),
    url(r'^sysadmin/', include(sysadmin_patterns)),

    # course offering URL hierarchy: many apps sub-included there
    # among them: discipline, discuss, groups, marking, pages, submission
    url(r'^' + COURSE_SLUG + '/', include(offering_patterns)),

    # nicely self-contained apps
    url(r'^advising/', include(advisornotes_patterns)),
    url(r'^alerts/', include(alerts_patterns)),
    url(r'^discipline/', include(discipline_patterns)),
    url(r'^faculty/', include(faculty_patterns)),
    url(r'^forms/', include(forms_patterns)),
    url(r'^gpacalc/', include(gpaconvert_patterns)),
    url(r'^reports/', include(report_patterns)),

    # graduate student-related apps
    url(r'^grad/', include(grad_patterns)),
    url(r'^ra/', include(ra_patterns)),
    url(r'^ta/', include(ta_patterns)),
    url(r'^tugs/', include(tug_patterns)),
    url(r'^my_grads/$', 'grad.views.supervisor_index'),

    # redirect old mobile URLs to rightful locations
    url(r'^m/(?P<urltail>.*)$',  RedirectView.as_view(url='/%(urltail)s/', permanent=True)),
    # accept the URL provided by User.get_absolute_url
    url(r'^users/' + USERID_SLUG + '/$', RedirectView.as_view(url='/sysadmin/users/%(userid)s/', permanent=True)),
]

if settings.DEPLOY_MODE != 'production':
    # URLs for development only:
    urlpatterns += [
        url(r'^fake_login', 'dashboard.views.fake_login'),
        url(r'^fake_logout', 'dashboard.views.fake_logout'),
    ]

