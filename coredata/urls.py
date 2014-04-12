from django.conf.urls import url
from courselib.urlparts import COURSE_SLUG, USERID_OR_EMPLID, USERID_SLUG

data_patterns = [ # prefix /data/
    url(r'^courses/(?P<semester>\d{4})$', 'dashboard.views.courses_json'),
    url(r'^offerings$', 'coredata.views.offerings_search'),
    url(r'^courses$', 'coredata.views.course_search'),
    url(r'^offering$', 'coredata.views.offering_by_id'),
    url(r'^students$', 'coredata.views.student_search'),
    #url(r'^sims_people', 'coredata.views.sims_person_search'),
    url(r'^scholarships/(?P<student_id>\d{9})$', 'ra.views.search_scholarships_by_student'),
]

admin_patterns = [ # prefix /admin/
    url(r'^$', 'coredata.views.unit_admin'),
    url(r'^roles/$', 'coredata.views.unit_role_list'),
    url(r'^roles/(?P<role_id>\d+)/delete$', 'coredata.views.delete_unit_role'),
    url(r'^roles/new$', 'coredata.views.new_unit_role'),
    url(r'^signatures/$', 'dashboard.views.signatures'),
    url(r'^signatures/new$', 'dashboard.views.new_signature'),
    url(r'^signatures/' + USERID_SLUG + '/view$', 'dashboard.views.view_signature'),
    url(r'^signatures/' + USERID_SLUG + '/delete', 'dashboard.views.delete_signature'),
    url(r'^(?P<unit_slug>[\w-]+)/address$', 'coredata.views.unit_address'),
    url(r'^(?P<unit_slug>[\w-]+)/instr$', 'coredata.views.missing_instructors'),
]

sysadmin_patterns = [ # prefix /sysadmin/
    url(r'^$', 'coredata.views.sysadmin'),
    url(r'^log/$', 'log.views.index'),
    url(r'^roles/$', 'coredata.views.role_list'),
    url(r'^roles/(?P<role_id>\d+)/delete$', 'coredata.views.delete_role'),
    url(r'^roles/new$', 'coredata.views.new_role'),
    url(r'^units/$', 'coredata.views.unit_list'),
    url(r'^units/new$', 'coredata.views.edit_unit'),
    url(r'^units/(?P<unit_slug>[\w-]+)/edit$', 'coredata.views.edit_unit'),
    url(r'^members/$', 'coredata.views.members_list'),
    url(r'^members/new$', 'coredata.views.edit_member'),
    url(r'^members/(?P<member_id>\d+)/edit$', 'coredata.views.edit_member'),
    url(r'^semesters/$', 'coredata.views.semester_list'),
    url(r'^semesters/new$', 'coredata.views.edit_semester'),
    url(r'^semesters/edit/(?P<semester_name>\d{4})$', 'coredata.views.edit_semester'),
    url(r'^users/' + USERID_OR_EMPLID + '/$', 'coredata.views.user_summary'),
    url(r'^offerings/' + COURSE_SLUG + '/$', 'coredata.views.offering_summary'),
    url(r'^people/new$', 'coredata.views.new_person'),
    url(r'^dishonesty/$', 'discipline.views.show_templates'),
    url(r'^dishonesty/new$', 'discipline.views.new_template'),
    url(r'^dishonesty/edit/(?P<template_id>\d+)$', 'discipline.views.edit_template'),
    url(r'^dishonesty/delete/(?P<template_id>\d+)$', 'discipline.views.delete_template'),
]