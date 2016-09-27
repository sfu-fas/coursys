from django.conf.urls import url
from courselib.urlparts import USERID_OR_EMPLID, ACCOUNT_SLUG, PROJECT_SLUG, RA_SLUG, SLUG_RE, ID_RE


ATTACH_SLUG = '(?P<attach_slug>' + SLUG_RE + ')'
PROGRAM_SLUG = '(?P<program_slug>' + SLUG_RE + ')'
PROGRAM_ID = '(?P<program_id>' + ID_RE + ')'

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
    url(r'^programs/new$', 'ra.views.new_program'),
    url(r'^programs/$', 'ra.views.programs_index'),
    url(r'^programs/' + PROGRAM_ID + '/delete$', 'ra.views.delete_program'),
    url(r'^programs/' + PROGRAM_SLUG + '/edit$', 'ra.views.edit_program'),
    url(r'^semesters/$', 'ra.views.semester_config'),
    url(r'^semesters/(?P<semester_name>\d+)$', 'ra.views.semester_config'),
    url(r'^' + RA_SLUG + '/$', 'ra.views.view'),
    url(r'^' + RA_SLUG + '/form$', 'ra.views.form'),
    url(r'^' + RA_SLUG + '/letter$', 'ra.views.letter'),
    url(r'^' + RA_SLUG + '/edit$', 'ra.views.edit'),
    url(r'^' + RA_SLUG + '/edit_letter$', 'ra.views.edit_letter'),
    url(r'^' + RA_SLUG + '/reappoint$', 'ra.views.reappoint'),
    url(r'^' + RA_SLUG + '/delete$', 'ra.views.delete_ra'),
    url(r'^' + RA_SLUG + '/select_letter$', 'ra.views.select_letter'),
    url(r'^' + RA_SLUG + '/select_letter/' + '(?P<print_only>[\w\-]+)' + '$', 'ra.views.select_letter'),
    url(r'^' + RA_SLUG + '/new_attach$', 'ra.views.new_attachment'),
    url(r'^' + RA_SLUG + '/attach/' + ATTACH_SLUG + '/delete$', 'ra.views.delete_attachment'),
    url(r'^' + RA_SLUG + '/attach/' + ATTACH_SLUG + '/view', 'ra.views.view_attachment'),
    url(r'^' + RA_SLUG + '/attach/' + ATTACH_SLUG + '/download$', 'ra.views.download_attachment'),
]
