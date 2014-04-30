from django.conf.urls import url
from courselib.urlparts import USERID_OR_EMPLID, ACCOUNT_SLUG, PROJECT_SLUG, RA_SLUG

ra_patterns = [ # prefix /ra/
    url(r'^$', 'ra.views.search'),
    url(r'^search/' + USERID_OR_EMPLID + '/$', 'ra.views.student_appointments'),
    url(r'^new$', 'ra.views.new'),
    url(r'^browse', 'ra.views.browse'),
    url(r'^found', 'ra.views.found'),
    url(r'^_payperiods$', 'ra.views.pay_periods'),
    url(r'^_personinfo$', 'ra.views.person_info'),
    url(r'^new/' + USERID_OR_EMPLID + '/$', 'ra.views.new_student'),
    url(r'^accounts/new$', 'ra.views.new_account'),
    url(r'^accounts/$', 'ra.views.accounts_index'),
    url(r'^accounts/' + ACCOUNT_SLUG + '/delete$', 'ra.views.remove_account'),
    url(r'^accounts/' + ACCOUNT_SLUG + '/edit$', 'ra.views.edit_account'),
    url(r'^projects/new$', 'ra.views.new_project'),
    url(r'^projects/$', 'ra.views.projects_index'),
    url(r'^projects/' + PROJECT_SLUG + '/delete$', 'ra.views.remove_project'),
    url(r'^projects/' + PROJECT_SLUG + '/edit$', 'ra.views.edit_project'),
    url(r'^semesters/$', 'ra.views.semester_config'),
    url(r'^semesters/(?P<semester_name>\d+)$', 'ra.views.semester_config'),
    url(r'^' + RA_SLUG + '/$', 'ra.views.view'),
    url(r'^' + RA_SLUG + '/form$', 'ra.views.form'),
    url(r'^' + RA_SLUG + '/letter$', 'ra.views.letter'),
    url(r'^' + RA_SLUG + '/edit$', 'ra.views.edit'),
    url(r'^' + RA_SLUG + '/edit_letter$', 'ra.views.edit_letter'),
    url(r'^' + RA_SLUG + '/reappoint$', 'ra.views.reappoint'),
    url(r'^' + RA_SLUG + '/delete$', 'ra.views.delete_ra'),

]