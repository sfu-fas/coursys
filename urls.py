from django.conf.urls.defaults import *
from django.conf import settings

if not settings.DEPLOYED:
    from django.contrib import admin
    admin.autodiscover()

from courselib.urlparts import *

handler404 = 'courselib.auth.NotFoundResponse'

#---------------------------------------

from advisors.models import *


urlpatterns = patterns('advisors.views',
    url(r'^advisors/$','index'),
    url(r'^view/$', 'search'),
	url(r'^search_detail/' + USERID_SLUG + '$', 'view_notes'),
	url(r'^success/' + USERID_SLUG + '$', 'add_notes'),
	url(r'^delete_notes/' + USERID_SLUG + '/(?P<note_id>\w+)/$', 'delete_notes'),
#    (r'^(?P<advisor_id>\w+)/(?P<student_id>\w+)/create/$','create'),
#    (r'^(?P<advisor_id>\w+)/(?P<student_id>\w+)/submit/$', 'submit'),
#    (r'^search_form/$', 'search_form'),
#    (r'^search/$', 'search_result'),

)
#---------------------------------------

urlpatterns += patterns('planning.views',
	
	url(r'^teaching/$', 'instructor_index'),
	url(r'^teaching/courses$', 'edit_capability'),
	url(r'^teaching/semesters$', 'edit_intention'),
	url(r'^teaching/submit_intention$', 'submit_intention'),
	url(r'^teaching/teachable/delete/(?P<course_id>\w+)/$', 'delete_course_from_capability'),
	
	
	url(r'^planning/$', 'admin_index'),
	url(r'^planning/new_course$', 'add_course'),
	url(r'^planning/submit_course', 'submit_course'),
	url(r'^planning/new_plan$', 'add_plan'),
	url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '/edit$', 'edit_plan'),
	url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '/courses$', 'edit_courses'),
	#url(r'^planning/add_courses_to_plan/(?P<plan_id>\w+)/$', 'add_courses_to_plan'),
	url(r'^planning/delete_course_from_plan/(?P<course_id>\w+)/(?P<plan_id>\w+)/$', 'delete_course_from_plan'),
	url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '/instructors$', 'assign_instructors'),
	url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '/assign/(?P<offering_id>\d+)$', 'submit_assigned_instructors'),
	url(r'^planning/activate_plan/(?P<plan_id>\w+)/$', 'activate_plan'),
	url(r'^planning/inactivate_plan/(?P<plan_id>\w+)/$', 'inactivate_plan'),
	url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '/delete$', 'delete_plan'),
	url(r'^planning/' + SEMESTER + '/' + PLAN_SLUG + '/assign/(?P<course_id>\w+)/$', 'view_instructors'),
	
	
	
	
	
	
	
)



#---------------------------------------
urlpatterns += patterns('',
    url(r'^login/$', 'django_cas.views.login'),
    url(r'^logout/$', 'django_cas.views.logout', {'next_page': '/'}),
	
#---------------------------------------
    url(r'^$', 'dashboard.views.index'),
        url(r'^m/$', 'mobile.views.index'),
    url(r'^' + 'news/$', 'dashboard.views.news_list'),
    url(r'^' + 'news/configure$', 'dashboard.views.news_config'),
    url(r'^' + 'news/configure/new$', 'dashboard.views.create_news_url'),
    url(r'^' + 'news/configure/del$', 'dashboard.views.disable_news_url'),
    url(r'^' + 'news/(?P<token>[0-9a-f]{32})/' + USERID_SLUG + '$', 'dashboard.views.atom_feed'),
    url(r'^' + 'docs/$', 'dashboard.views.list_docs'),
    url(r'^' + 'docs/(?P<doc_slug>' + SLUG_RE + ')$', 'dashboard.views.view_doc'),

    url(r'^' + COURSE_SLUG + '/$', 'grades.views.course_info'),
        url(r'^m/' + COURSE_SLUG + '/$', 'mobile.views.course_info'),
    url(r'^' + COURSE_SLUG + '/_reorder_activity$', 'grades.views.reorder_activity'),
    url(r'^' + COURSE_SLUG + '/_new_message$', 'dashboard.views.new_message'),
    url(r'^' + COURSE_SLUG + '/_url$', 'grades.views.course_url'),

    url(r'^' + COURSE_SLUG + '/_groups$', 'django.views.generic.simple.redirect_to', {'url': '/%(course_slug)s/_groups/'}),
    url(r'^' + COURSE_SLUG + '/_groups/$', 'groups.views.groupmanage'),
    url(r'^' + COURSE_SLUG + '/_groups/_new$', 'groups.views.create'),
    url(r'^' + COURSE_SLUG + '/_groups/_assignStudent$', 'groups.views.assign_student'),
    url(r'^' + COURSE_SLUG + '/_groups/_submit$', 'groups.views.submit'),
    url(r'^' + COURSE_SLUG + '/_groups/' + ACTIVITY_SLUG + '$', 'groups.views.groupmanage'),
    url(r'^' + COURSE_SLUG + '/_groups/invite/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.invite'),
    url(r'^' + COURSE_SLUG + '/_groups/join/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.join'),
    url(r'^' + COURSE_SLUG + '/_groups/reject/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.reject'),
    url(r'^' + COURSE_SLUG + '/_groups/(?P<group_slug>' + SLUG_RE + ')/remove$', 'groups.views.remove_student'),
    url(r'^' + COURSE_SLUG + '/_groups/(?P<group_slug>' + SLUG_RE + ')/add$', 'groups.views.assign_student'),
    url(r'^' + COURSE_SLUG + '/_groups/(?P<group_slug>' + SLUG_RE + ')/rename$', 'groups.views.change_name'),

    url(r'^' + COURSE_SLUG + '/_grades$', 'grades.views.all_grades'),
    url(r'^' + COURSE_SLUG + '/_grades_csv$', 'grades.views.all_grades_csv'),
    url(r'^' + COURSE_SLUG + '/_activity_choice$', 'grades.views.activity_choice'),
    url(r'^' + COURSE_SLUG + '/_new_numeric$', 'grades.views.add_numeric_activity'),
    url(r'^' + COURSE_SLUG + '/_new_letter$', 'grades.views.add_letter_activity'),
    url(r'^' + COURSE_SLUG + '/_new_cal_numeric$', 'grades.views.add_cal_numeric_activity'),
    url(r'^' + COURSE_SLUG + '/_new_cal_letter$', 'grades.views.add_cal_letter_activity'),
    url(r'^' + COURSE_SLUG + '/_formula_tester$', 'grades.views.formula_tester'),
    url(r'^' + COURSE_SLUG + '/_students/$', 'grades.views.student_search'),
    url(r'^' + COURSE_SLUG + '/_students/' + USERID_SLUG + '$', 'grades.views.student_info'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '$', 'grades.views.activity_info'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/_stat$', 'grades.views.activity_stat'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/_cal_all$', 'grades.views.calculate_all'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/_cal_idv_ajax$', 'grades.views.calculate_individual_ajax'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/' + USERID_SLUG + '/_cal_idv$', 'grades.views.calculate_individual'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/edit$', 'grades.views.edit_activity'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/groups$', 'grades.views.activity_info_with_groups'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/release$', 'grades.views.release_activity'),

    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/$', 'submission.views.show_components'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/history$', 'submission.views.show_components_submission_history'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/download$', 'submission.views.download_activity_files'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/components/new$', 'submission.views.add_component'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/components/edit$', 'submission.views.edit_single'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/' + COMPONENT_SLUG + '/' + SUBMISSION_ID + '/get$', 'submission.views.download_file'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/' + USERID_SLUG + '/get$', 'submission.views.download_file'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/' + USERID_SLUG + '/view$', 'submission.views.show_student_submission_staff'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/' + USERID_SLUG + '/history$', 'submission.views.show_components_submission_history'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/' + GROUP_SLUG + '/mark$', 'submission.views.take_ownership_and_mark'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/submission/' + USERID_SLUG + '/mark$', 'submission.views.take_ownership_and_mark'),

    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/$', 'marking.views.manage_activity_components'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/positions/$', 'marking.views.manage_component_positions'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/common$', 'marking.views.manage_common_problems'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/new/students/' + USERID_SLUG + '/$', 'marking.views.marking_student'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/new/groups/' + GROUP_SLUG + '/$', 'marking.views.marking_group'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/markall/students$', 'marking.views.mark_all_students'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/markall/groups$', 'marking.views.mark_all_groups'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/markall/students/cal$', 'marking.views.mark_all_students_cal'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/markall/groups/cal$', 'marking.views.mark_all_groups_cal'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/markall/students/lettergrade$', 'marking.views.mark_all_students_lettergrade'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/markall/students/cal/lettergrade$', 'marking.views.mark_all_students_cal_lettergrade'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/markall/groups/lettergrade$', 'marking.views.mark_all_groups_lettergrade'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/markall/groups/cal/lettergrade$', 'marking.views.mark_all_groups_cal_lettergrade'),
    
    url(r'^' + COURSE_ACTIVITY_SLUG + '/gradestatus/lettergrade' + USERID_SLUG + '/$', 'marking.views.change_grade_status_lettergrade'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/students/' + USERID_SLUG + '/$', 'marking.views.mark_summary_student'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/groups/' + GROUP_SLUG + '/$', 'marking.views.mark_summary_group'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/students/' + USERID_SLUG + '/history', 'marking.views.mark_history_student'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/groups/' + GROUP_SLUG + '/history', 'marking.views.mark_history_group'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/' + ACTIVITY_MARK_ID + '/attachment', 'marking.views.download_marking_attachment'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/import$', 'marking.views.import_components'),

    url(r'^' + COURSE_ACTIVITY_SLUG + '/gradestatus/' + USERID_SLUG + '/$', 'marking.views.change_grade_status'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/csv$', 'marking.views.export_csv'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/csv_lettergrade$', 'marking.views.export_csv_lettergrade'),
    url(r'^' + COURSE_SLUG + '/_copysetup/$', 'marking.views.copy_course_setup'),

    url(r'^discipline/$', 'discipline.views.all_cases'),
    url(r'^discipline/' + COURSE_SLUG + '/' + CASE_SLUG + '$', 'discipline.views.show_chair'),
    url(r'^' + COURSE_SLUG + '/_dishonesty/$', 'discipline.views.index'),
    url(r'^' + COURSE_SLUG + '/_dishonesty/new$', 'discipline.views.new'),
    url(r'^' + COURSE_SLUG + '/_dishonesty/newgroup$', 'discipline.views.newgroup'),
    url(r'^' + COURSE_SLUG + '/_dishonesty/new_nonstudent$', 'discipline.views.new_nonstudent'),
    url(r'^' + COURSE_SLUG + '/_dishonesty/clusters/' + DGROUP_SLUG + '$', 'discipline.views.showgroup'),
    url(r'^' + COURSE_SLUG + '/_dishonesty/cases/' + CASE_SLUG + '$', 'discipline.views.show'),
    url(r'^' + COURSE_SLUG + '/_dishonesty/cases/' + CASE_SLUG + '/related$', 'discipline.views.edit_related'),
    url(r'^' + COURSE_SLUG + '/_dishonesty/cases/' + CASE_SLUG + '/letter$', 'discipline.views.view_letter'),
    url(r'^' + COURSE_SLUG + '/_dishonesty/cases/' + CASE_SLUG + '/attach$', 'discipline.views.edit_attach'),
    url(r'^' + COURSE_SLUG + '/_dishonesty/cases/' + CASE_SLUG + '/attach/new$', 'discipline.views.new_file'),
    url(r'^' + COURSE_SLUG + '/_dishonesty/cases/' + CASE_SLUG + '/attach/(?P<fileid>\d+)$', 'discipline.views.download_file'),
    url(r'^' + COURSE_SLUG + '/_dishonesty/cases/' + CASE_SLUG + '/attach/(?P<fileid>\d+)/edit$', 'discipline.views.edit_file'),
    url(r'^' + COURSE_SLUG + '/_dishonesty/cases/' + CASE_SLUG + '/(?P<field>[a-z_]+)$', 'discipline.views.edit_case_info'),

    url(r'^sysadmin/$', 'coredata.views.sysadmin'),
    url(r'^sysadmin/log/$', 'log.views.index'),
    url(r'^sysadmin/roles/$', 'coredata.views.role_list'),
    url(r'^sysadmin/roles/(?P<role_id>\d+)/delete$', 'coredata.views.delete_role'),
    url(r'^sysadmin/roles/new$', 'coredata.views.new_role'),
    url(r'^sysadmin/roles/instr$', 'coredata.views.missing_instructors'),
    url(r'^sysadmin/members/$', 'coredata.views.members_list'),
    url(r'^sysadmin/members/new$', 'coredata.views.edit_member'),
    url(r'^sysadmin/members/(?P<member_id>\d+)/edit$', 'coredata.views.edit_member'),
    url(r'^users/' + USERID_SLUG + '/$', 'django.views.generic.simple.redirect_to', {'url': '/sysadmin/users/%(userid)s/'}), # accept the URL provided as get_absolute_url for user objects
    url(r'^sysadmin/users/' + USERID_SLUG + '/$', 'coredata.views.user_summary'),
    url(r'^sysadmin/people/new$', 'coredata.views.new_person'),
    url(r'^sysadmin/dishonesty/$', 'discipline.views.show_templates'),
    url(r'^sysadmin/dishonesty/new$', 'discipline.views.new_template'),
    url(r'^sysadmin/dishonesty/edit/(?P<template_id>\d+)$', 'discipline.views.edit_template'),
    url(r'^sysadmin/dishonesty/delete/(?P<template_id>\d+)$', 'discipline.views.delete_template'),

)
if not settings.DEPLOYED:
    # URLs for development only:
    urlpatterns += patterns('',
        (r'^admin/(.*)', admin.site.root),
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT}),
    )

