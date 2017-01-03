from django.conf.urls import url
from courselib.urlparts import USERID_OR_EMPLID, ACCOUNT_SLUG, PROJECT_SLUG, RA_SLUG, SLUG_RE, ID_RE


ATTACH_SLUG = '(?P<attach_slug>' + SLUG_RE + ')'
PROGRAM_SLUG = '(?P<program_slug>' + SLUG_RE + ')'
PROGRAM_ID = '(?P<program_id>' + ID_RE + ')'

ra_patterns = [ # prefix /ra/
    url(r'^$', 'ra.views.search', name='search'),
    url(r'^search/' + USERID_OR_EMPLID + '/$', 'ra.views.student_appointments', name='student_appointments'),
    url(r'^new$', 'ra.views.new', name='new'),
    url(r'^browse', 'ra.views.browse', name='browse'),
    url(r'^found', 'ra.views.found', name='found'),
    url(r'^_payperiods$', 'ra.views.pay_periods', name='pay_periods'),
    url(r'^_personinfo$', 'ra.views.person_info', name='person_info'),
    url(r'^new/' + USERID_OR_EMPLID + '/$', 'ra.views.new_student', name='new_student'),
    url(r'^accounts/new$', 'ra.views.new_account', name='new_account'),
    url(r'^accounts/$', 'ra.views.accounts_index', name='accounts_index'),
    url(r'^accounts/' + ACCOUNT_SLUG + '/delete$', 'ra.views.remove_account', name='remove_account'),
    url(r'^accounts/' + ACCOUNT_SLUG + '/edit$', 'ra.views.edit_account', name='edit_account'),
    url(r'^projects/new$', 'ra.views.new_project', name='new_project'),
    url(r'^projects/$', 'ra.views.projects_index', name='projects_index'),
    url(r'^projects/' + PROJECT_SLUG + '/delete$', 'ra.views.remove_project', name='remove_project'),
    url(r'^projects/' + PROJECT_SLUG + '/edit$', 'ra.views.edit_project', name='edit_project'),
    url(r'^programs/new$', 'ra.views.new_program', name='new_program'),
    url(r'^programs/$', 'ra.views.programs_index', name='programs_index'),
    url(r'^programs/' + PROGRAM_ID + '/delete$', 'ra.views.delete_program', name='delete_program'),
    url(r'^programs/' + PROGRAM_SLUG + '/edit$', 'ra.views.edit_program', name='edit_program'),
    url(r'^semesters/$', 'ra.views.semester_config', name='semester_config'),
    url(r'^semesters/(?P<semester_name>\d+)$', 'ra.views.semester_config', name='semester_config'),
    url(r'^' + RA_SLUG + '/$', 'ra.views.view', name='view'),
    url(r'^' + RA_SLUG + '/form$', 'ra.views.form', name='form'),
    url(r'^' + RA_SLUG + '/letter$', 'ra.views.letter', name='letter'),
    url(r'^' + RA_SLUG + '/edit$', 'ra.views.edit', name='edit'),
    url(r'^' + RA_SLUG + '/edit_letter$', 'ra.views.edit_letter', name='edit_letter'),
    url(r'^' + RA_SLUG + '/reappoint$', 'ra.views.reappoint', name='reappoint'),
    url(r'^' + RA_SLUG + '/delete$', 'ra.views.delete_ra', name='delete_ra'),
    url(r'^' + RA_SLUG + '/select_letter$', 'ra.views.select_letter', name='select_letter'),
    url(r'^' + RA_SLUG + '/select_letter/' + '(?P<print_only>[\w\-]+)' + '$', 'ra.views.select_letter', name='select_letter'),
    url(r'^' + RA_SLUG + '/new_attach$', 'ra.views.new_attachment', name='new_attachment'),
    url(r'^' + RA_SLUG + '/attach/' + ATTACH_SLUG + '/delete$', 'ra.views.delete_attachment', name='delete_attachment'),
    url(r'^' + RA_SLUG + '/attach/' + ATTACH_SLUG + '/view', 'ra.views.view_attachment', name='view_attachment'),
    url(r'^' + RA_SLUG + '/attach/' + ATTACH_SLUG + '/download$', 'ra.views.download_attachment', name='download_attachment'),
]
