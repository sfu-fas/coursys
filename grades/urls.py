from django.conf.urls import url, include
from django.views.generic import RedirectView
from courselib.urlparts import USERID_SLUG, ACTIVITY_SLUG

from discipline.urls import discipline_offering_patterns
from discuss.urls import discussion_patterns
from groups.urls import group_patterns
from marking.urls import marking_patterns
from pages.urls import pages_patterns
from submission.urls import submission_patterns, similarity_patterns
from quizzes.urls import quiz_patterns
from forum.urls import forum_patterns

import grades.views as grades_views
import marking.views as marking_views
import coredata.views as coredata_views
import ta.views as ta_views

activity_patterns = [ # prefix /COURSE_SLUG/+ACTIVITY_SLUG/
    url(r'^$', grades_views.activity_info, name='activity_info'),
    url(r'^stat$', grades_views.activity_stat, name='activity_stat'),
    url(r'^cal_all$', grades_views.calculate_all, name='calculate_all'),
    url(r'^cal_all_letter$', grades_views.calculate_all_lettergrades, name='calculate_all_lettergrades'),
    url(r'^cal_idv_ajax$', grades_views.calculate_individual_ajax, name='calculate_individual_ajax'),
    url(r'^official$', grades_views.compare_official, name='compare_official'),
    url(r'^change/' + USERID_SLUG + '$', grades_views.grade_change, name='grade_change'),
    #url(r'^' + USERID_SLUG + '/cal_idv$', grades_views.calculate_individual, name='calculate_individual'),
    url(r'^edit$', grades_views.edit_activity, name='edit_activity'),
    url(r'^cutoffs$', grades_views.edit_cutoffs, name='edit_cutoffs'),
    url(r'^groups$', grades_views.activity_info_with_groups, name='activity_info_with_groups'),
    url(r'^release$', grades_views.release_activity, name='release_activity'),
    url(r'^delete$', grades_views.delete_activity, name='delete_activity'),

    url(r'^gradestatus/' + USERID_SLUG + '/$', marking_views.change_grade_status, name='change_grade_status'),
    url(r'^csv$', marking_views.export_csv, name='export_csv'),
    url(r'^sims_csv$', marking_views.export_sims, name='export_sims'),

    url(r'^markall/students$', marking_views.mark_all_students, name='mark_all_students'),
    url(r'^markall/groups$', marking_views.mark_all_groups, name='mark_all_groups'),

    url(r'^submission/', include((submission_patterns, 'submission'), namespace='submission')),
    url(r'^similarity/', include((similarity_patterns, 'similarity'), namespace='similarity')),
    url(r'^marking/', include((marking_patterns, 'marking'), namespace='marking')),
    url(r'^quiz/', include((quiz_patterns, 'quiz'), namespace='quiz')),
]

offering_patterns = [ # prefix /COURSE_SLUG/
    url(r'^$', grades_views.course_info, name='course_info'),
    url(r'^reorder_activity$', grades_views.reorder_activity, name='reorder_activity'),
    url(r'^new_message$', grades_views.new_message, name='new_message'),
    url(r'^config/$', grades_views.course_config, name='course_config'),
    url(r'^config/tas$', coredata_views.manage_tas, name='manage_tas'),
    url(r'^config/copysetup$', marking_views.copy_course_setup, name='copy_course_setup'),

    url(r'^grades$', grades_views.all_grades, name='all_grades'),
    url(r'^grades_csv$', grades_views.all_grades_csv, name='all_grades_csv'),
    url(r'^activity_choice$', grades_views.activity_choice, name='activity_choice'),
    url(r'^new_numeric$', grades_views.add_numeric_activity, name='add_numeric_activity'),
    url(r'^new_letter$', grades_views.add_letter_activity, name='add_letter_activity'),
    url(r'^new_cal_numeric$', grades_views.add_cal_numeric_activity, name='add_cal_numeric_activity'),
    url(r'^new_cal_letter$', grades_views.add_cal_letter_activity, name='add_cal_letter_activity'),
    url(r'^formula_tester$', grades_views.formula_tester, name='formula_tester'),
    url(r'^list$', grades_views.class_list, name='class_list'),
    url(r'^photolist$', grades_views.photo_list, name='photo_list'),
    url(r'^photolist-(?P<style>\w+)$', grades_views.photo_list, name='photo_list'),
    url(r'^students/$', grades_views.student_search, name='student_search'),
    url(r'^students/' + USERID_SLUG + '$', grades_views.student_info, name='student_info'),
    url(r'^grade-history$', grades_views.grade_history, name='grade_history'),
    url(r'^export$', grades_views.export_all, name='export_all'),

    url(r'^config/tugs/' + USERID_SLUG + '/$', ta_views.view_tug, name='view_tug'),
    url(r'^config/tugs/' + USERID_SLUG + '/new$', ta_views.new_tug, name='new_tug'),
    url(r'^config/tugs/' + USERID_SLUG + '/edit$', ta_views.edit_tug, name='edit_tug'),
    url(r'^config/taoffers/$', ta_views.ta_offers, name='ta_offers'),

    url(r'^groups$', RedirectView.as_view(url='/%(course_slug)s/groups/', permanent=True)),
    url(r'^groups/', include((group_patterns, 'groups'), namespace='groups')),
    url(r'^discussion/', include((discussion_patterns, 'discussion'), namespace='discussion')),
    url(r'^forum/', include((forum_patterns, 'forum'), namespace='forum')),

    url(r'^\+' + ACTIVITY_SLUG + '/', include(activity_patterns)),
    url(r'^dishonesty/', include((discipline_offering_patterns, 'discipline'), namespace='discipline')),
    url(r'^pages/', include((pages_patterns, 'pages'), namespace='pages')),

    # redirect for old-style activity URLs (must be last to avoid conflict with other rules)
    url(r'^' + ACTIVITY_SLUG + '/(?P<tail>.*)$', grades_views.activity_info_oldurl, name='activity_info_oldurl'),
]
