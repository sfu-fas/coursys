from django.conf.urls import url
from courselib.urlparts import COURSE_SLUG, CASE_SLUG, DGROUP_SLUG
import discipline.views as discipline_views

discipline_patterns = [ # prefix /discipline/
    url(r'^$', discipline_views.chair_index, name='chair_index'),
    url(r'^admin$', discipline_views.permission_admin, name='permission_admin'),
    url(r'^admin/add$', discipline_views.permission_admin_add, name='permission_admin_add'),
    url(r'^' + COURSE_SLUG + '/' + CASE_SLUG + '/create$', discipline_views.chair_create, name='chair_create'),
    url(r'^' + COURSE_SLUG + '/' + CASE_SLUG + '/$', discipline_views.chair_show, name='chair_show'),
    url(r'^' + COURSE_SLUG + '/' + CASE_SLUG + '/instr$', discipline_views.chair_show_instr, name='chair_show_instr'),
]

discipline_offering_patterns = [ # prefix /COURSE_SLUG/dishonesty/
    url(r'^$', discipline_views.index, name='index'),
    url(r'^new$', discipline_views.new, name='new'),
    url(r'^newgroup$', discipline_views.newgroup, name='newgroup'),
    url(r'^new_nonstudent$', discipline_views.new_nonstudent, name='new_nonstudent'),
    url(r'^clusters/' + DGROUP_SLUG + '$', discipline_views.showgroup, name='showgroup'),
    url(r'^cases/' + CASE_SLUG + '$', discipline_views.show, name='show'),
    url(r'^cases/' + CASE_SLUG + '/related$', discipline_views.edit_related, name='edit_related'),
    url(r'^cases/' + CASE_SLUG + '/letter$', discipline_views.view_letter, name='view_letter'),
    url(r'^cases/' + CASE_SLUG + '/attach$', discipline_views.edit_attach, name='edit_attach'),
    url(r'^cases/' + CASE_SLUG + '/attach/new$', discipline_views.new_file, name='new_file'),
    url(r'^cases/' + CASE_SLUG + '/attach/(?P<fileid>\d+)$', discipline_views.download_file, name='download_file'),
    url(r'^cases/' + CASE_SLUG + '/attach/(?P<fileid>\d+)/edit$', discipline_views.edit_file, name='edit_file'),
    url(r'^cases/' + CASE_SLUG + '/(?P<field>[a-z_]+)$', discipline_views.edit_case_info, name='edit_case_info'),
]
