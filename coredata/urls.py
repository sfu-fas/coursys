from django.urls import re_path as url
from courselib.urlparts import COURSE_SLUG, USERID_OR_EMPLID, USERID_SLUG, \
                               EMPLID_SLUG, SEMESTER, UNIT_SLUG, SEMESTER

import coredata.views as coredata_views
import grades.views as grades_views
import ra.views as ra_views
import dashboard.views as dashboard_views
import discipline.views as discipline_views
import log.views as log_views

data_patterns = [ # prefix /data/
#    url(r'^courses/(?P<semester>\d{4})$', dashboard_views.courses_json, name='courses_json'),
    url(r'^offerings$', coredata_views.offerings_search, name='offerings_search'),
    url(r'^offerings_slug$', coredata_views.offerings_slug_search, name='offerings_slug_search'),
    url(r'^offerings_slug/'+SEMESTER+'$', coredata_views.offerings_slug_search, name='offerings_slug_search'),
    url(r'^courses$', coredata_views.course_search, name='course_search'),
    url(r'^offering$', coredata_views.offering_by_id, name='offering_by_id'),
    url(r'^students$', coredata_views.student_search, name='student_search'),
    #url(r'^sims_people', coredata_views.sims_person_search, name='sims_person_search'),
    url(r'^scholarships/(?P<student_id>\d{9})$', ra_views.search_scholarships_by_student, name='search_scholarships_by_student'),
    url(r'^photos/' + EMPLID_SLUG + '$', grades_views.student_photo, name='student_photo'),
    url(r'^roles/' + EMPLID_SLUG + '$', coredata_views.roles, name='roles'),
]

admin_patterns = [ # prefix /admin/
    url(r'^$', coredata_views.unit_admin, name='unit_admin'),
    url(r'^new_temporary_person$', coredata_views.new_temporary_person, name='new_temporary_person'),
    url(r'^roles/$', coredata_views.unit_role_list, name='unit_role_list'),
    url(r'^roles/(?P<role_id>\d+)/delete$', coredata_views.delete_unit_role, name='delete_unit_role'),
    url(r'^roles/multiple/renew/$', coredata_views.renew_unit_roles, name='renew_unit_roles'),
    url(r'^roles/renew$', coredata_views.renew_unit_roles_list, name='renew_unit_roles_list'),
    url(r'^roles/new$', coredata_views.new_unit_role, name='new_unit_role'),
    url(r'^roles/offboarding$', coredata_views.offboard_unit, name='offboard_unit'),
    url(r'^signatures/$', dashboard_views.signatures, name='signatures'),
    url(r'^signatures/new$', dashboard_views.new_signature, name='new_signature'),
    url(r'^signatures/' + USERID_SLUG + '/view$', dashboard_views.view_signature, name='view_signature'),
    url(r'^signatures/' + USERID_SLUG + '/delete', dashboard_views.delete_signature, name='delete_signature'),
    url(r'^(?P<unit_slug>[\w-]+)/address$', coredata_views.unit_address, name='unit_address'),
    url(r'^(?P<unit_slug>[\w-]+)/instr$', coredata_views.missing_instructors, name='missing_instructors'),
]

sysadmin_patterns = [ # prefix /sysadmin/
    url(r'^$', coredata_views.sysadmin, name='sysadmin'),
    url(r'^log/$', log_views.index, name='index'),
    url(r'^roles/$', coredata_views.role_list, name='role_list'),
    url(r'^roles/expired$', coredata_views.expired_role_list, name='expired_role_list'),
    url(r'^roles/(?P<role_id>\d+)/delete$', coredata_views.delete_role, name='delete_role'),
    url(r'^roles/(?P<role_id>\d+)/renew', coredata_views.renew_role, name='renew_role'),
    url(r'^roles/new$', coredata_views.new_role, name='new_role'),
    url(r'^units/$', coredata_views.unit_list, name='unit_list'),
    url(r'^units/new$', coredata_views.edit_unit, name='edit_unit'),
    url(r'^units/(?P<unit_slug>[\w-]+)/edit$', coredata_views.edit_unit, name='edit_unit'),
    url(r'^members/$', coredata_views.members_list, name='members_list'),
    url(r'^members/new$', coredata_views.edit_member, name='edit_member'),
    url(r'^members/(?P<member_id>\d+)/edit$', coredata_views.edit_member, name='edit_member'),
    url(r'^semesters/$', coredata_views.semester_list, name='semester_list'),
    url(r'^semesters/new$', coredata_views.edit_semester, name='edit_semester'),
    url(r'^semesters/edit/(?P<semester_name>\d{4})$', coredata_views.edit_semester, name='edit_semester'),
    url(r'^users/' + USERID_OR_EMPLID + '/$', coredata_views.user_summary, name='user_summary'),
    url(r'^users/' + USERID_OR_EMPLID + '/config/$', coredata_views.user_config, name='user_config'),
    url(r'^offerings/' + COURSE_SLUG + '/$', coredata_views.offering_summary, name='offering_summary'),
    url(r'^combined/$', coredata_views.combined_offerings, name='combined_offerings'),
    url(r'^combined/new$', coredata_views.new_combined, name='new_combined'),
    url(r'^combined/add/(?P<pk>\d+)$', coredata_views.add_combined_offering, name='add_combined_offering'),
    url(r'^people/new$', coredata_views.new_person, name='new_person'),
    url(r'^dishonesty/$', discipline_views.show_templates, name='show_templates'),
    url(r'^dishonesty/new$', discipline_views.new_template, name='new_template'),
    url(r'^dishonesty/edit/(?P<template_id>\d+)$', discipline_views.edit_template, name='edit_template'),
    url(r'^dishonesty/delete/(?P<template_id>\d+)$', discipline_views.delete_template, name='delete_template'),
    url(r'^panel$', coredata_views.admin_panel, name='admin_panel'),
    url(r'^anypersons/$', coredata_views.list_anypersons, name='list_anypersons'),
    url(r'^anyperson/delete/(?P<anyperson_id>\d+)$', coredata_views.delete_anyperson, name='delete_anyperson'),
    url(r'^anyperson/new/$', coredata_views.add_anyperson, name='add_anyperson'),
    url(r'^anyperson/edit/(?P<anyperson_id>\d+)$', coredata_views.edit_anyperson, name='edit_anyperson'),
    url(r'^anyperson/cleanup/$', coredata_views.delete_empty_anypersons, name='delete_empty_anypersons'),
    url(r'^futurepersons/$', coredata_views.list_futurepersons, name='list_futurepersons'),
    url(r'^futureperson/delete/(?P<futureperson_id>\d+)$', coredata_views.delete_futureperson, name='delete_futureperson'),
    url(r'^futureperson/view/(?P<futureperson_id>\d+)$', coredata_views.view_futureperson, name='view_futureperson'),
    url(r'^futureperson/new/$', coredata_views.add_futureperson, name='add_futureperson'),
    url(r'^futureperson/edit/(?P<futureperson_id>\d+)$', coredata_views.edit_futureperson, name='edit_futureperson'),
    url(r'^roleaccounts/$', coredata_views.list_roleaccounts, name='list_roleaccounts'),
    url(r'^roleaccount/delete/(?P<roleaccount_id>\d+)$', coredata_views.delete_roleaccount, name='delete_roleaccount'),
    url(r'^roleaccount/new/$', coredata_views.add_roleaccount, name='add_roleaccount'),
    url(r'^roleaccount/edit/(?P<roleaccount_id>\d+)$', coredata_views.edit_roleaccount, name='edit_roleaccount'),
    url(r'^logging/$', log_views.log_explore, name='log_explore'),
    url(r'^logging/(?P<log_type>\w+)/(?P<log_id>[0-9a-z\-]+)$', log_views.log_view, name='log_view'),
]

browse_patterns = [ # prefix /browse/
    url(r'^$', coredata_views.browse_courses, name='browse_courses'),
    url(r'^info/' + COURSE_SLUG + '$', coredata_views.browse_courses_info, name='browse_courses_info'),
    url(r'^enrolment/' + COURSE_SLUG + '$', coredata_views.course_enrolment, name='course_enrolment'),
    url(r'^enrolment/' + COURSE_SLUG + '/download$', coredata_views.course_enrolment_download, name='course_enrolment_download'),
    url(r'^pages/$', coredata_views.course_home_pages, name='course_home_pages'),
    url(r'^pages/' + UNIT_SLUG + '$', coredata_views.course_home_pages_unit, name='course_home_pages_unit'),
    url(r'^pages/' + UNIT_SLUG + '/' + SEMESTER + '$', coredata_views.course_home_pages_unit, name='course_home_pages_unit'),
    url(r'^pages/admin/' + COURSE_SLUG + '$', coredata_views.course_home_admin, name='course_home_admin'),
    url(r'^pages/' + UNIT_SLUG + '/$', coredata_views.course_home_pages_unit, name='course_home_pages_unit'),          
    url(r'^' + UNIT_SLUG + '$', coredata_views.browse_courses, name='browse_courses'),
    url(r'^' + UNIT_SLUG + '/(?P<campus>[a-zA-Z]{1,9})$', coredata_views.browse_courses, name='browse_courses'),    
]
