from django.conf.urls import url
from courselib.urlparts import COURSE_SLUG, USERID_OR_EMPLID, USERID_SLUG, \
                               EMPLID_SLUG, SEMESTER, UNIT_SLUG, SEMESTER

data_patterns = [ # prefix /data/
#    url(r'^courses/(?P<semester>\d{4})$', 'dashboard.views.courses_json', name='courses_json'),
    url(r'^offerings$', 'coredata.views.offerings_search', name='offerings_search'),
    url(r'^offerings_slug$', 'coredata.views.offerings_slug_search', name='offerings_slug_search'),
    url(r'^offerings_slug/'+SEMESTER+'$', 'coredata.views.offerings_slug_search', name='offerings_slug_search'),
    url(r'^courses$', 'coredata.views.course_search', name='course_search'),
    url(r'^offering$', 'coredata.views.offering_by_id', name='offering_by_id'),
    url(r'^students$', 'coredata.views.student_search', name='student_search'),
    #url(r'^sims_people', 'coredata.views.sims_person_search', name='sims_person_search'),
    url(r'^scholarships/(?P<student_id>\d{9})$', 'ra.views.search_scholarships_by_student', name='search_scholarships_by_student'),
    url(r'^photos/' + EMPLID_SLUG + '$', 'grades.views.student_photo', name='student_photo'),
]

admin_patterns = [ # prefix /admin/
    url(r'^$', 'coredata.views.unit_admin', name='unit_admin'),
    url(r'^new_temporary_person$', 'coredata.views.new_temporary_person', name='new_temporary_person'),
    url(r'^roles/$', 'coredata.views.unit_role_list', name='unit_role_list'),
    url(r'^roles/(?P<role_id>\d+)/delete$', 'coredata.views.delete_unit_role', name='delete_unit_role'),
    url(r'^roles/new$', 'coredata.views.new_unit_role', name='new_unit_role'),
    url(r'^signatures/$', 'dashboard.views.signatures', name='signatures'),
    url(r'^signatures/new$', 'dashboard.views.new_signature', name='new_signature'),
    url(r'^signatures/' + USERID_SLUG + '/view$', 'dashboard.views.view_signature', name='view_signature'),
    url(r'^signatures/' + USERID_SLUG + '/delete', 'dashboard.views.delete_signature', name='delete_signature'),
    url(r'^(?P<unit_slug>[\w-]+)/address$', 'coredata.views.unit_address', name='unit_address'),
    url(r'^(?P<unit_slug>[\w-]+)/instr$', 'coredata.views.missing_instructors', name='missing_instructors'),
]

sysadmin_patterns = [ # prefix /sysadmin/
    url(r'^$', 'coredata.views.sysadmin', name='sysadmin'),
    url(r'^log/$', 'log.views.index', name='index'),
    url(r'^roles/$', 'coredata.views.role_list', name='role_list'),
    url(r'^roles/(?P<role_id>\d+)/delete$', 'coredata.views.delete_role', name='delete_role'),
    url(r'^roles/new$', 'coredata.views.new_role', name='new_role'),
    url(r'^units/$', 'coredata.views.unit_list', name='unit_list'),
    url(r'^units/new$', 'coredata.views.edit_unit', name='edit_unit'),
    url(r'^units/(?P<unit_slug>[\w-]+)/edit$', 'coredata.views.edit_unit', name='edit_unit'),
    url(r'^members/$', 'coredata.views.members_list', name='members_list'),
    url(r'^members/new$', 'coredata.views.edit_member', name='edit_member'),
    url(r'^members/(?P<member_id>\d+)/edit$', 'coredata.views.edit_member', name='edit_member'),
    url(r'^semesters/$', 'coredata.views.semester_list', name='semester_list'),
    url(r'^semesters/new$', 'coredata.views.edit_semester', name='edit_semester'),
    url(r'^semesters/edit/(?P<semester_name>\d{4})$', 'coredata.views.edit_semester', name='edit_semester'),
    url(r'^users/' + USERID_OR_EMPLID + '/$', 'coredata.views.user_summary', name='user_summary'),
    url(r'^offerings/' + COURSE_SLUG + '/$', 'coredata.views.offering_summary', name='offering_summary'),
    url(r'^combined/$', 'coredata.views.combined_offerings', name='combined_offerings'),
    url(r'^combined/new$', 'coredata.views.new_combined', name='new_combined'),
    url(r'^combined/add/(?P<pk>\d+)$', 'coredata.views.add_combined_offering', name='add_combined_offering'),
    url(r'^people/new$', 'coredata.views.new_person', name='new_person'),
    url(r'^dishonesty/$', 'discipline.views.show_templates', name='show_templates'),
    url(r'^dishonesty/new$', 'discipline.views.new_template', name='new_template'),
    url(r'^dishonesty/edit/(?P<template_id>\d+)$', 'discipline.views.edit_template', name='edit_template'),
    url(r'^dishonesty/delete/(?P<template_id>\d+)$', 'discipline.views.delete_template', name='delete_template'),
    url(r'^panel$', 'coredata.views.admin_panel', name='admin_panel'),
    url(r'^anypersons/$', 'coredata.views.list_anypersons', name='list_anypersons'),
    url(r'^anyperson/delete/(?P<anyperson_id>\d+)$', 'coredata.views.delete_anyperson', name='delete_anyperson'),
    url(r'^anyperson/new/$', 'coredata.views.add_anyperson', name='add_anyperson'),
    url(r'^anyperson/edit/(?P<anyperson_id>\d+)$', 'coredata.views.edit_anyperson', name='edit_anyperson'),
    url(r'^anyperson/cleanup/$', 'coredata.views.delete_empty_anypersons', name='delete_empty_anypersons'),
    url(r'^futurepersons/$', 'coredata.views.list_futurepersons', name='list_futurepersons'),
    url(r'^futureperson/delete/(?P<futureperson_id>\d+)$', 'coredata.views.delete_futureperson', name='delete_futureperson'),
    url(r'^futureperson/view/(?P<futureperson_id>\d+)$', 'coredata.views.view_futureperson', name='view_futureperson'),
    url(r'^futureperson/new/$', 'coredata.views.add_futureperson', name='add_futureperson'),
    url(r'^futureperson/edit/(?P<futureperson_id>\d+)$', 'coredata.views.edit_futureperson', name='edit_futureperson'),
    url(r'^roleaccounts/$', 'coredata.views.list_roleaccounts', name='list_roleaccounts'),
    url(r'^roleaccount/delete/(?P<roleaccount_id>\d+)$', 'coredata.views.delete_roleaccount', name='delete_roleaccount'),
    url(r'^roleaccount/new/$', 'coredata.views.add_roleaccount', name='add_roleaccount'),
    url(r'^roleaccount/edit/(?P<roleaccount_id>\d+)$', 'coredata.views.edit_roleaccount', name='edit_roleaccount'),



]

browse_patterns = [ # prefix /browse/
    url(r'^$', 'coredata.views.browse_courses', name='browse_courses'),
    url(r'^info/' + COURSE_SLUG + '$', 'coredata.views.browse_courses_info', name='browse_courses_info'),
    url(r'^pages/$', 'coredata.views.course_home_pages', name='course_home_pages'),
    url(r'^pages/' + UNIT_SLUG + '$', 'coredata.views.course_home_pages_unit', name='course_home_pages_unit'),
    url(r'^pages/' + UNIT_SLUG + '/' + SEMESTER + '$', 'coredata.views.course_home_pages_unit', name='course_home_pages_unit'),
    url(r'^pages/admin/' + COURSE_SLUG + '$', 'coredata.views.course_home_admin', name='course_home_admin'),
]
