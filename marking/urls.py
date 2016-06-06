from django.conf.urls import url
from courselib.urlparts import USERID_SLUG, ACTIVITY_MARK_ID, GROUP_SLUG

marking_patterns = [ # prefix /COURSE_SLUG/+ACTIVITY_SLUG/marking/
    url(r'^$', 'marking.views.manage_activity_components'),
    url(r'^positions$', 'marking.views.manage_component_positions'),
    url(r'^common$', 'marking.views.manage_common_problems'),
    url(r'^import$', 'marking.views.import_marks'),
    url(r'^export$', 'marking.views.export_marks'),
    url(r'^new/students/' + USERID_SLUG + '/$', 'marking.views.marking_student'),
    url(r'^new/groups/' + GROUP_SLUG + '/$', 'marking.views.marking_group'),

    url(r'^students/' + USERID_SLUG + '/$', 'marking.views.mark_summary_student'),
    url(r'^groups/' + GROUP_SLUG + '/$', 'marking.views.mark_summary_group'),
    url(r'^students/' + USERID_SLUG + '/history', 'marking.views.mark_history_student'),
    url(r'^groups/' + GROUP_SLUG + '/history', 'marking.views.mark_history_group'),
    url(r'^' + ACTIVITY_MARK_ID + '/attachment', 'marking.views.download_marking_attachment'),
    #url(r'^rubric$', 'marking.views.import_components'),
]