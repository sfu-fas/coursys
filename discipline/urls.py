from django.urls import re_path as url
from courselib.urlparts import COURSE_SLUG, CASE_SLUG, DGROUP_SLUG
import discipline.views as discipline_views

discipline_patterns = [ # prefix /discipline/
    url(r'^$', discipline_views.chair_index, name='chair_index'),
    url(r'^csv$', discipline_views.chair_csv, name='chair_csv'),
    url(r'^admin/$', discipline_views.permission_admin, name='permission_admin'),
    url(r'^admin/add$', discipline_views.permission_admin_add, name='permission_admin_add'),
    url(r'^' + COURSE_SLUG + '/' + CASE_SLUG + '/instr$', discipline_views.chair_show_instr, name='chair_show_instr'),
    url(r'^' + COURSE_SLUG + '/' + CASE_SLUG + '/update$', discipline_views.central_updates, name='central_updates'),
]

discipline_offering_patterns = [ # prefix /COURSE_SLUG/dishonesty/
    url(r'^$', discipline_views.index, name='index'),
    url(r'^preview$', discipline_views.markup_preview, name='markup_preview'),
    url(r'^new$', discipline_views.new, name='new'),
    url(r'^newgroup$', discipline_views.newgroup, name='newgroup'),
    url(r'^new_nonstudent$', discipline_views.new_nonstudent, name='new_nonstudent'),
    url(r'^clusters/' + DGROUP_SLUG + '$', discipline_views.showgroup, name='showgroup'),

    url(r'^cases/' + CASE_SLUG + '$', discipline_views.show, name='show'),
    url(r'^cases/' + CASE_SLUG + '/notify$', discipline_views.CaseNotify.as_view(), name='notify'),
    url(r'^cases/' + CASE_SLUG + '/response$', discipline_views.CaseResponse.as_view(), name='response'),
    url(r'^cases/' + CASE_SLUG + '/facts$', discipline_views.CaseFacts.as_view(), name='facts'),
    url(r'^cases/' + CASE_SLUG + '/penalty$', discipline_views.CasePenalty.as_view(), name='penalty'),
    url(r'^cases/' + CASE_SLUG + '/send$', discipline_views.CaseSend.as_view(), name='send'),
    url(r'^cases/' + CASE_SLUG + '/notes$', discipline_views.CaseNotes.as_view(), name='notes'),
    url(r'^cases/' + CASE_SLUG + '/implemented$', discipline_views.CasePenaltyImplemented.as_view(), name='penalty_implemented'),

    url(r'^cases/' + CASE_SLUG + '/letter$', discipline_views.view_letter, name='view_letter'),
    url(r'^cases/' + CASE_SLUG + '/attach$', discipline_views.edit_attach, name='edit_attach'),
    url(r'^cases/' + CASE_SLUG + '/attach/new$', discipline_views.new_file, name='new_file'),
    url(r'^cases/' + CASE_SLUG + '/attach/delete', discipline_views.CaseDeleteAttachment.as_view(), name='delete_attachment'),
    url(r'^cases/' + CASE_SLUG + '/attach/(?P<fileid>\d+)$', discipline_views.download_file, name='download_file'),
    #url(r'^cases/' + CASE_SLUG + '/attach/(?P<fileid>\d+)/edit$', discipline_views.edit_file, name='edit_file'),
]
