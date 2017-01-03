from django.conf.urls import url
from courselib.urlparts import COURSE_SLUG, CASE_SLUG, DGROUP_SLUG

discipline_patterns = [ # prefix /discipline/
    url(r'^$', 'discipline.views.chair_index', name='chair_index'),
    url(r'^' + COURSE_SLUG + '/' + CASE_SLUG + '/create$', 'discipline.views.chair_create', name='chair_create'),
    url(r'^' + COURSE_SLUG + '/' + CASE_SLUG + '/$', 'discipline.views.chair_show', name='chair_show'),
    url(r'^' + COURSE_SLUG + '/' + CASE_SLUG + '/instr$', 'discipline.views.chair_show_instr', name='chair_show_instr'),
]

discipline_offering_patterns = [ # prefix /COURSE_SLUG/dishonesty/
    url(r'^$', 'discipline.views.index', name='index'),
    url(r'^new$', 'discipline.views.new', name='new'),
    url(r'^newgroup$', 'discipline.views.newgroup', name='newgroup'),
    url(r'^new_nonstudent$', 'discipline.views.new_nonstudent', name='new_nonstudent'),
    url(r'^clusters/' + DGROUP_SLUG + '$', 'discipline.views.showgroup', name='showgroup'),
    url(r'^cases/' + CASE_SLUG + '$', 'discipline.views.show', name='show'),
    url(r'^cases/' + CASE_SLUG + '/related$', 'discipline.views.edit_related', name='edit_related'),
    url(r'^cases/' + CASE_SLUG + '/letter$', 'discipline.views.view_letter', name='view_letter'),
    url(r'^cases/' + CASE_SLUG + '/attach$', 'discipline.views.edit_attach', name='edit_attach'),
    url(r'^cases/' + CASE_SLUG + '/attach/new$', 'discipline.views.new_file', name='new_file'),
    url(r'^cases/' + CASE_SLUG + '/attach/(?P<fileid>\d+)$', 'discipline.views.download_file', name='download_file'),
    url(r'^cases/' + CASE_SLUG + '/attach/(?P<fileid>\d+)/edit$', 'discipline.views.edit_file', name='edit_file'),
    url(r'^cases/' + CASE_SLUG + '/(?P<field>[a-z_]+)$', 'discipline.views.edit_case_info', name='edit_case_info'),
]
