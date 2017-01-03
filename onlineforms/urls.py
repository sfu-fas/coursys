from django.conf.urls import url
from courselib.urlparts import USERID_OR_EMPLID, SLUG_RE

FORM_SLUG = '(?P<form_slug>' + SLUG_RE + ')'
SHEET_SLUG = '(?P<sheet_slug>' + SLUG_RE + ')'
FIELD_SLUG = '(?P<field_slug>' + SLUG_RE + ')'
FORMSUBMIT_SLUG = '(?P<formsubmit_slug>' + SLUG_RE + ')'
SHEETSUBMIT_SLUG = '(?P<sheetsubmit_slug>' + SLUG_RE + ')'
FORMGROUP_SLUG = '(?P<formgroup_slug>' + SLUG_RE + ')'
SECRET_SUBMIT_URL = '(?P<secret_url>' + SLUG_RE + ')'

forms_patterns = [
    url(r'^groups/$', 'onlineforms.views.manage_groups', name='manage_groups'),
    url(r'^groups/new$', 'onlineforms.views.new_group', name='new_group'),
    url(r'^groups/' + FORMGROUP_SLUG + '/$', 'onlineforms.views.manage_group', name='manage_group'),
    url(r'^groups/' + FORMGROUP_SLUG + '/add$', 'onlineforms.views.add_group_member', name='add_group_member'),
    url(r'^groups/' + FORMGROUP_SLUG + '/remove/' + USERID_OR_EMPLID + '/$', 'onlineforms.views.remove_group_member', name='remove_group_member'),

    url(r'^admin/$', 'onlineforms.views.admin_list_all', name='admin_list_all'),
    url(r'^admin/assign$', 'onlineforms.views.admin_assign_any', name='admin_assign_any'),
    url(r'^admin/assign-nonsfu$', 'onlineforms.views.admin_assign_any_nonsfu', name='admin_assign_any_nonsfu'),

    url(r'^admin/completed/$', 'onlineforms.views.admin_completed', name='admin_completed'),
    url(r'^admin/completed/' + FORM_SLUG + '/$', 'onlineforms.views.admin_completed_form', name='admin_completed_form'),
    url(r'^admin/completed/' + FORM_SLUG + '/summary$', 'onlineforms.views.summary_csv', name='summary_csv'),

    url(r'^admin/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/assign$', 'onlineforms.views.admin_assign', name='admin_assign'),
    url(r'^admin/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/assign-nonsfu$', 'onlineforms.views.admin_assign_nonsfu', name='admin_assign_nonsfu'),
    url(r'^admin/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/give', 'onlineforms.views.admin_change_owner', name='admin_change_owner'),
    url(r'^admin/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/' + SHEETSUBMIT_SLUG + '/return', 'onlineforms.views.admin_return_sheet', name='admin_return_sheet'),

    url(r'^manage/$', 'onlineforms.views.list_all', name='list_all'),
    url(r'^manage/new$', 'onlineforms.views.new_form', name='new_form'),
    url(r'^manage/' + FORM_SLUG + '/$', 'onlineforms.views.view_form', name='view_form'),
    url(r'^manage/' + FORM_SLUG + '/edit$', 'onlineforms.views.edit_form', name='edit_form'),
    url(r'^manage/' + FORM_SLUG + '/new$', 'onlineforms.views.new_sheet', name='new_sheet'),
    url(r'^manage/' + FORM_SLUG + '/preview$', 'onlineforms.views.preview_form', name='preview_form'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/preview$', 'onlineforms.views.preview_sheet', name='preview_sheet'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/$', 'onlineforms.views.edit_sheet', name='edit_sheet'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/edit$', 'onlineforms.views.edit_sheet_info', name='edit_sheet_info'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/reorder$', 'onlineforms.views.reorder_field', name='reorder_field'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/new$', 'onlineforms.views.new_field', name='new_field'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/field-' + FIELD_SLUG + '$', 'onlineforms.views.edit_field', name='edit_field'),

    url(r'^$', 'onlineforms.views.index', name='index'),
    url(r'^participated/$', 'onlineforms.views.participated_in', name='participated_in'),
    url(r'^view/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/$', 'onlineforms.views.view_submission', name='view_submission'),
    url(r'^view/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/' + '(?P<action>\w+)/' + '(?P<file_id>\d+)/$', 'onlineforms.views.file_field_download', name='file_field_download'),
    url(r'^' + FORM_SLUG + '/$', 'onlineforms.views.sheet_submission_initial', name='sheet_submission_initial'),
    url(r'^' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/' + SHEET_SLUG + '/' + SHEETSUBMIT_SLUG + '$', 'onlineforms.views.sheet_submission_subsequent', name='sheet_submission_subsequent'),
    url(r'^submission/' + SECRET_SUBMIT_URL + '/$', 'onlineforms.views.sheet_submission_via_url', name='sheet_submission_via_url'),
    url(r'^' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/' + SHEET_SLUG + '/' + SHEETSUBMIT_SLUG + '/reject$', 'onlineforms.views.reject_sheet_subsequent', name='reject_sheet_subsequent'),
    url(r'^submission/' + SECRET_SUBMIT_URL + '/reject$', 'onlineforms.views.reject_sheet_via_url', name='reject_sheet_via_url'),
]
