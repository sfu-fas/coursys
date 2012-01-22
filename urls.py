from django.conf.urls.defaults import *
from django.conf import settings
from django.views.generic.simple import direct_to_template

if not settings.DEPLOYED:
    from django.contrib import admin
    admin.autodiscover()

from courselib.urlparts import *

handler404 = 'courselib.auth.NotFoundResponse'

urlpatterns = patterns('')

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
	url(r'^planning/copy_plan$', 'copy_plan'),
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

	url(r'^semester_plans/$', 'semester_plan_index'),
	url(r'^semester_plans/' + SEMESTER + '/view$', 'view_semester_plan'),
)



#---------------------------------------
urlpatterns += patterns('',
    url(r'^login/$', 'django_cas.views.login'),
    url(r'^logout/$', 'django_cas.views.logout', {'next_page': '/'}),
    url(r'^logout/(?P<next_page>.*)/$', 'django_cas.views.logout', name='auth_logout_next'),
    url(r'^robots.txt$', direct_to_template, {'template': 'robots.txt', 'mimetype': 'text/plain'}),
	
#---------------------------------------
    url(r'^$', 'dashboard.views.index'),
        url(r'^m/$', 'mobile.views.index'),
    url(r'^' + 'favicon.ico$', 'django.views.generic.simple.redirect_to', {'url': '/media/icons/favicon.ico'}),
    url(r'^' + 'config/$', 'dashboard.views.config'),
    url(r'^' + 'news/$', 'dashboard.views.news_list'),
    url(r'^' + 'news/configure/$', 'django.views.generic.simple.redirect_to', {'url': '/config/'}),
    #url(r'^' + 'calendar/$', 'django.views.generic.simple.redirect_to', {'url': '/config/'}),
    url(r'^' + 'config/news/set$', 'dashboard.views.create_news_url'),
    url(r'^' + 'config/news/del$', 'dashboard.views.disable_news_url'),
    url(r'^' + 'config/calendar/set$', 'dashboard.views.create_calendar_url'),
    url(r'^' + 'config/calendar/del$', 'dashboard.views.disable_calendar_url'),
    url(r'^' + 'config/news$', 'dashboard.views.news_config'),
    url(r'^' + 'news/(?P<token>[0-9a-f]{32})/' + USERID_SLUG + '$', 'dashboard.views.atom_feed'),
    url(r'^' + 'news/(?P<token>[0-9a-f]{32})/' + USERID_SLUG + '/' + COURSE_SLUG + '$', 'dashboard.views.atom_feed'),
    url(r'^' + 'calendar/(?P<token>[0-9a-f]{32})/' + USERID_SLUG + '$', 'dashboard.views.calendar_ical'),
    url(r'^' + 'calendar/$', 'dashboard.views.calendar'),
    url(r'^' + 'calendar/data$', 'dashboard.views.calendar_data'),
    url(r'^' + 'docs/$', 'dashboard.views.list_docs'),
    url(r'^' + 'docs/(?P<doc_slug>' + SLUG_RE + ')$', 'dashboard.views.view_doc'),
    url(r'^data/courses/(?P<semester>\d{4})$', 'dashboard.views.courses_json'),
    url(r'^data/offerings$', 'coredata.views.offerings_search'),
    url(r'^data/offering$', 'coredata.views.offering_by_id'),

    url(r'^' + COURSE_SLUG + '/$', 'grades.views.course_info'),
        url(r'^m/' + COURSE_SLUG + '/$', 'mobile.views.course_info'),
    url(r'^' + COURSE_SLUG + '/reorder_activity$', 'grades.views.reorder_activity'),
    url(r'^' + COURSE_SLUG + '/new_message$', 'dashboard.views.new_message'),
    url(r'^' + COURSE_SLUG + '/config/$', 'grades.views.course_config'),
    url(r'^' + COURSE_SLUG + '/config/tas$', 'coredata.views.manage_tas'),

    url(r'^' + COURSE_SLUG + '/groups$', 'django.views.generic.simple.redirect_to', {'url': '/%(course_slug)s/groups/'}),
    url(r'^' + COURSE_SLUG + '/groups/$', 'groups.views.groupmanage'),
    url(r'^' + COURSE_SLUG + '/groups/new$', 'groups.views.create'),
    url(r'^' + COURSE_SLUG + '/groups/assignStudent$', 'groups.views.assign_student'),
    url(r'^' + COURSE_SLUG + '/groups/submit$', 'groups.views.submit'),
    url(r'^' + COURSE_SLUG + '/groups/for/' + ACTIVITY_SLUG + '$', 'groups.views.groupmanage'),
    url(r'^' + COURSE_SLUG + '/groups/invite/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.invite'),
    url(r'^' + COURSE_SLUG + '/groups/join/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.join'),
    url(r'^' + COURSE_SLUG + '/groups/reject/(?P<group_slug>' + SLUG_RE + ')$', 'groups.views.reject'),
    url(r'^' + COURSE_SLUG + '/groups/(?P<group_slug>' + SLUG_RE + ')/remove$', 'groups.views.remove_student'),
    url(r'^' + COURSE_SLUG + '/groups/(?P<group_slug>' + SLUG_RE + ')/add$', 'groups.views.assign_student'),
    url(r'^' + COURSE_SLUG + '/groups/(?P<group_slug>' + SLUG_RE + ')/rename$', 'groups.views.change_name'),

    url(r'^' + COURSE_SLUG + '/grades$', 'grades.views.all_grades'),
    url(r'^' + COURSE_SLUG + '/grades_csv$', 'grades.views.all_grades_csv'),
    url(r'^' + COURSE_SLUG + '/activity_choice$', 'grades.views.activity_choice'),
    url(r'^' + COURSE_SLUG + '/new_numeric$', 'grades.views.add_numeric_activity'),
    url(r'^' + COURSE_SLUG + '/new_letter$', 'grades.views.add_letter_activity'),
    url(r'^' + COURSE_SLUG + '/new_cal_numeric$', 'grades.views.add_cal_numeric_activity'),
    url(r'^' + COURSE_SLUG + '/new_cal_letter$', 'grades.views.add_cal_letter_activity'),
    url(r'^' + COURSE_SLUG + '/formula_tester$', 'grades.views.formula_tester'),
    url(r'^' + COURSE_SLUG + '/list/$', 'grades.views.class_list'),
        url(r'^m/' + COURSE_SLUG + '/list/$', 'mobile.views.class_list'),
    url(r'^' + COURSE_SLUG + '/students/$', 'grades.views.student_search'),
    url(r'^' + COURSE_SLUG + '/students/' + USERID_SLUG + '$', 'grades.views.student_info'),
        url(r'^m/' + COURSE_SLUG + '/students/' + USERID_SLUG + '$', 'mobile.views.student_info'),
        url(r'^m/' + COURSE_SLUG + '/search/$', 'mobile.views.student_search'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '$', 'grades.views.activity_info'),
        url(r'^m/' + COURSE_ACTIVITY_SLUG + '$', 'mobile.views.activity_info'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/stat$', 'grades.views.activity_stat'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/cal_all$', 'grades.views.calculate_all'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/cal_all_letter$', 'grades.views.calculate_all_lettergrades'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/cal_idv_ajax$', 'grades.views.calculate_individual_ajax'),
    #url(r'^' + COURSE_ACTIVITY_SLUG + '/' + USERID_SLUG + '/cal_idv$', 'grades.views.calculate_individual'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/edit$', 'grades.views.edit_activity'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/cutoffs$', 'grades.views.edit_cutoffs'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/groups$', 'grades.views.activity_info_with_groups'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/release$', 'grades.views.release_activity'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/delete$', 'grades.views.delete_activity'),

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

    url(r'^' + COURSE_ACTIVITY_SLUG + '/markall/students$', 'marking.views.mark_all_students'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/markall/groups$', 'marking.views.mark_all_groups'),

    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/$', 'marking.views.manage_activity_components'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/positions$', 'marking.views.manage_component_positions'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/common$', 'marking.views.manage_common_problems'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/import$', 'marking.views.import_marks'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/export$', 'marking.views.export_marks'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/new/students/' + USERID_SLUG + '/$', 'marking.views.marking_student'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/new/groups/' + GROUP_SLUG + '/$', 'marking.views.marking_group'),
    
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/students/' + USERID_SLUG + '/$', 'marking.views.mark_summary_student'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/groups/' + GROUP_SLUG + '/$', 'marking.views.mark_summary_group'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/students/' + USERID_SLUG + '/history', 'marking.views.mark_history_student'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/groups/' + GROUP_SLUG + '/history', 'marking.views.mark_history_group'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/' + ACTIVITY_MARK_ID + '/attachment', 'marking.views.download_marking_attachment'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/marking/rubric$', 'marking.views.import_components'),

    url(r'^' + COURSE_ACTIVITY_SLUG + '/gradestatus/' + USERID_SLUG + '/$', 'marking.views.change_grade_status'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/csv$', 'marking.views.export_csv'),
    url(r'^' + COURSE_ACTIVITY_SLUG + '/sims_csv$', 'marking.views.export_sims'),
    url(r'^' + COURSE_SLUG + '/copysetup/$', 'marking.views.copy_course_setup'),

    url(r'^' + COURSE_SLUG + '/pages/$', 'pages.views.index_page'),
    url(r'^' + COURSE_SLUG + '/pages/_all$', 'pages.views.all_pages'),
    url(r'^' + COURSE_SLUG + '/pages/_new$', 'pages.views.new_page'),
    url(r'^' + COURSE_SLUG + '/pages/_newfile$', 'pages.views.new_file'),
    url(r'^' + COURSE_SLUG + '/pages/' + PAGE_LABEL + '$', 'pages.views.view_page'),
    url(r'^' + COURSE_SLUG + '/pages/' + PAGE_LABEL + '/view$', 'pages.views.view_file'),
    url(r'^' + COURSE_SLUG + '/pages/' + PAGE_LABEL + '/download$', 'pages.views.download_file'),
    url(r'^' + COURSE_SLUG + '/pages/' + PAGE_LABEL + '/edit$', 'pages.views.edit_page'),
    url(r'^' + COURSE_SLUG + '/pages/' + PAGE_LABEL + '/history$', 'pages.views.page_history'),
    url(r'^' + COURSE_SLUG + '/pages/' + PAGE_LABEL + '/version/(?P<version_id>\d+)$', 'pages.views.page_version'),

    #Start TUG URL mappings

    url(r'^' + COURSE_SLUG + '/config/tugs/$', 'ta.views.index_page'),
    url(r'^' + COURSE_SLUG + '/config/tugs/all$', 'ta.views.all_tugs'),
    url(r'^' + COURSE_SLUG + '/config/tugs/new$', 'ta.views.new_tug'),
    url(r'^' + COURSE_SLUG + '/config/tugs/' + USERID_SLUG + '/view$', 'ta.views.view_tug'),
    url(r'^' + COURSE_SLUG + '/config/tugs/' + USERID_SLUG + '/edit$', 'ta.views.edit_tug'),

    #End TUG URL mappings
    
    url(r'^discipline/$', 'discipline.views.chair_index'),
    url(r'^discipline/' + COURSE_SLUG + '/' + CASE_SLUG + '/create$', 'discipline.views.chair_create'),
    url(r'^discipline/' + COURSE_SLUG + '/' + CASE_SLUG + '/$', 'discipline.views.chair_show'),
    url(r'^discipline/' + COURSE_SLUG + '/' + CASE_SLUG + '/instr$', 'discipline.views.chair_show_instr'),

    url(r'^' + COURSE_SLUG + '/dishonesty/$', 'discipline.views.index'),
    url(r'^' + COURSE_SLUG + '/dishonesty/new$', 'discipline.views.new'),
    url(r'^' + COURSE_SLUG + '/dishonesty/newgroup$', 'discipline.views.newgroup'),
    url(r'^' + COURSE_SLUG + '/dishonesty/new_nonstudent$', 'discipline.views.new_nonstudent'),
    url(r'^' + COURSE_SLUG + '/dishonesty/clusters/' + DGROUP_SLUG + '$', 'discipline.views.showgroup'),
    url(r'^' + COURSE_SLUG + '/dishonesty/cases/' + CASE_SLUG + '$', 'discipline.views.show'),
    url(r'^' + COURSE_SLUG + '/dishonesty/cases/' + CASE_SLUG + '/related$', 'discipline.views.edit_related'),
    url(r'^' + COURSE_SLUG + '/dishonesty/cases/' + CASE_SLUG + '/letter$', 'discipline.views.view_letter'),
    url(r'^' + COURSE_SLUG + '/dishonesty/cases/' + CASE_SLUG + '/attach$', 'discipline.views.edit_attach'),
    url(r'^' + COURSE_SLUG + '/dishonesty/cases/' + CASE_SLUG + '/attach/new$', 'discipline.views.new_file'),
    url(r'^' + COURSE_SLUG + '/dishonesty/cases/' + CASE_SLUG + '/attach/(?P<fileid>\d+)$', 'discipline.views.download_file'),
    url(r'^' + COURSE_SLUG + '/dishonesty/cases/' + CASE_SLUG + '/attach/(?P<fileid>\d+)/edit$', 'discipline.views.edit_file'),
    url(r'^' + COURSE_SLUG + '/dishonesty/cases/' + CASE_SLUG + '/(?P<field>[a-z_]+)$', 'discipline.views.edit_case_info'),

    url(r'^' + COURSE_ACTIVITY_SLUG_OLD + '(?P<tail>.*)$', 'django.views.generic.simple.redirect_to', {'url': '/%(course_slug)s/@%(activity_slug)s%(tail)s'}), # redirect old activity URLs

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
    url(r'^sysadmin/semesters/$', 'coredata.views.semester_list'),
    url(r'^sysadmin/semesters/new$', 'coredata.views.edit_semester'),
    url(r'^sysadmin/semesters/edit/(?P<semester_name>\d{4})$', 'coredata.views.edit_semester'),
    url(r'^sysadmin/users/' + USERID_SLUG + '/$', 'coredata.views.user_summary'),
    url(r'^sysadmin/people/new$', 'coredata.views.new_person'),
    url(r'^sysadmin/dishonesty/$', 'discipline.views.show_templates'),
    url(r'^sysadmin/dishonesty/new$', 'discipline.views.new_template'),
    url(r'^sysadmin/dishonesty/edit/(?P<template_id>\d+)$', 'discipline.views.edit_template'),
    url(r'^sysadmin/dishonesty/delete/(?P<template_id>\d+)$', 'discipline.views.delete_template'),
    
    # Advisor Notes Start
    
    url(r'^advising/$', 'advisornotes.views.index'),
    url(r'^data/students$', 'advisornotes.views.student_search'),
    url(r'^advising/students/' + USERID_SLUG + '$', 'advisornotes.views.student_notes'),
    url(r'^advising/students/' + USERID_SLUG + '/notes/' + NOTE_ID + '$', 'advisornotes.views.view_note'),
    url(r'^advising/students/' + USERID_SLUG + '/notes/new', 'advisornotes.views.new_note'),
    
    #url(r'^notes/new$', 'advisornotes.views.new_note'),
    #url(r'^notes/' + NOTE_ID + '/view$', 'advisornotes.views.view_note'),
    #url(r'^notes/students$', 'advisornotes.views.student_search'),
    #url(r'^notes/students/' + USERID_SLUG + '$', 'advisornotes.views.student_notes'),
    
    # Advisor Notes End
    	
    # Graduate Student Records Start
    url(r'grad/$', 'grad.views.index'),
    #url(r'grad/'+ USERID_SLUG + '/manage', 'grad.views.manage'),
    url(r'grad/new', 'grad.views.new'),
    
    # Graduate Student Records Ends
    
    
)
if not settings.DEPLOYED:
    # URLs for development only:
    urlpatterns += patterns('',
        #(r'^admin/(.*)', admin.site.root),
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT}),
    )

