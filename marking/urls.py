from django.urls import re_path as url
from courselib.urlparts import USERID_SLUG, ACTIVITY_MARK_ID, GROUP_SLUG
import marking.views as marking_views

marking_patterns = [ # prefix /COURSE_SLUG/+ACTIVITY_SLUG/marking/
    url(r'^$', marking_views.manage_activity_components, name='manage_activity_components'),
    url(r'^positions$', marking_views.manage_component_positions, name='manage_component_positions'),
    url(r'^common$', marking_views.manage_common_problems, name='manage_common_problems'),
    url(r'^import$', marking_views.import_marks, name='import_marks'),
    url(r'^export$', marking_views.export_marks, name='export_marks'),
    url(r'^new/students/' + USERID_SLUG + '/$', marking_views.marking_student, name='marking_student'),
    url(r'^new/groups/' + GROUP_SLUG + '/$', marking_views.marking_group, name='marking_group'),

    url(r'^students/' + USERID_SLUG + '/$', marking_views.mark_summary_student, name='mark_summary_student'),
    url(r'^groups/' + GROUP_SLUG + '/$', marking_views.mark_summary_group, name='mark_summary_group'),
    url(r'^students/' + USERID_SLUG + '/history', marking_views.mark_history_student, name='mark_history_student'),
    url(r'^groups/' + GROUP_SLUG + '/history', marking_views.mark_history_group, name='mark_history_group'),
    url(r'^' + ACTIVITY_MARK_ID + '/attachment', marking_views.download_marking_attachment, name='download_marking_attachment'),
    #url(r'^rubric$', marking_views.import_components, name='import_components'),
]
