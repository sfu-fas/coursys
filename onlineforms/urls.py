from django.urls import re_path as url
from courselib.urlparts import USERID_OR_EMPLID, SLUG_RE
import onlineforms.views as onlineforms_views

FORM_SLUG = '(?P<form_slug>' + SLUG_RE + ')'
SHEET_SLUG = '(?P<sheet_slug>' + SLUG_RE + ')'
FIELD_SLUG = '(?P<field_slug>' + SLUG_RE + ')'
FORMSUBMIT_SLUG = '(?P<formsubmit_slug>' + SLUG_RE + ')'
SHEETSUBMIT_SLUG = '(?P<sheetsubmit_slug>' + SLUG_RE + ')'
FORMGROUP_SLUG = '(?P<formgroup_slug>' + SLUG_RE + ')'
SECRET_SUBMIT_URL = '(?P<secret_url>' + SLUG_RE + ')'

forms_patterns = [
    url(r'^groups/$', onlineforms_views.manage_groups, name='manage_groups'),
    url(r'^groups/new$', onlineforms_views.new_group, name='new_group'),
    url(r'^groups/' + FORMGROUP_SLUG + '/$', onlineforms_views.manage_group, name='manage_group'),
    url(r'^groups/' + FORMGROUP_SLUG + '/add$', onlineforms_views.add_group_member, name='add_group_member'),
    url(r'^groups/' + FORMGROUP_SLUG + '/remove/' + USERID_OR_EMPLID + '/$', onlineforms_views.remove_group_member,
        name='remove_group_member'),
    url(r'^groups/' + FORMGROUP_SLUG + '/toggle/' + USERID_OR_EMPLID + '/$', onlineforms_views.toggle_group_member,
        name='toggle_group_member'),

    url(r'^admin/$', onlineforms_views.admin_list_all, name='admin_list_all'),
    url(r'^admin/assign$', onlineforms_views.admin_assign_any, name='admin_assign_any'),
    url(r'^admin/assign-nonsfu$', onlineforms_views.admin_assign_any_nonsfu, name='admin_assign_any_nonsfu'),

    url(r'^admin/completed/$', onlineforms_views.admin_completed, name='admin_completed'),
    url(r'^admin/completed_deleted/$', onlineforms_views.admin_completed_deleted, name='admin_completed_deleted'),
    url(r'^admin/completed/' + FORM_SLUG + '/$', onlineforms_views.admin_completed_form, name='admin_completed_form'),
    url(r'^admin/rejected/' + FORM_SLUG + '/$', onlineforms_views.admin_rejected_form, name='admin_rejected_form'),
    url(r'^admin/completed/' + FORM_SLUG + '/summary$', onlineforms_views.summary_csv, name='summary_csv'),
    url(r'^admin/completed/' + FORM_SLUG + '/pending_summary$', onlineforms_views.pending_summary_csv,
        name='pending_summary_csv'),
    url(r'^admin/completed/' + FORM_SLUG + '/waiting_summary$', onlineforms_views.waiting_summary_csv,
        name='waiting_summary_csv'),
    url(r'^admin/bulk_close/', onlineforms_views.bulk_close, name='bulk_close'),
    url(r'^admin/completed/' + FORM_SLUG + '/download_result_csv$', onlineforms_views.download_result_csv, name='download_result_csv'),
    url(r'^admin/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/assign$', onlineforms_views.admin_assign, name='admin_assign'),
    url(r'^admin/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/assign-nonsfu$', onlineforms_views.admin_assign_nonsfu, name='admin_assign_nonsfu'),
    url(r'^admin/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/give', onlineforms_views.admin_change_owner, name='admin_change_owner'),
    url(r'^admin/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/' + SHEETSUBMIT_SLUG + '/return', onlineforms_views.admin_return_sheet, name='admin_return_sheet'),

    url(r'^manage/$', onlineforms_views.list_all, name='list_all'),
    url(r'^manage/new$', onlineforms_views.new_form, name='new_form'),
    url(r'^manage/' + FORM_SLUG + '/$', onlineforms_views.view_form, name='view_form'),
    url(r'^manage/' + FORM_SLUG + '/edit$', onlineforms_views.edit_form, name='edit_form'),
    url(r'^manage/' + FORM_SLUG + '/new$', onlineforms_views.new_sheet, name='new_sheet'),
    url(r'^manage/' + FORM_SLUG + '/preview$', onlineforms_views.preview_form, name='preview_form'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/preview$', onlineforms_views.preview_sheet, name='preview_sheet'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/$', onlineforms_views.edit_sheet, name='edit_sheet'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/edit$', onlineforms_views.edit_sheet_info, name='edit_sheet_info'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/reorder$', onlineforms_views.reorder_field, name='reorder_field'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/new$', onlineforms_views.new_field, name='new_field'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/field-' + FIELD_SLUG + '$', onlineforms_views.edit_field, name='edit_field'),

    url(r'^$', onlineforms_views.index, name='index'),
    url(r'^(?P<unit_slug>[\w-]+)/ajax_calls/form_search/$', onlineforms_views.formSearchAutocomplete),
    url(r'^index/(?P<unit_slug>[\w-]+)$', onlineforms_views.index, name='index'),
    url(r'^index/(?P<unit_slug>[\w-]+)/ajax_calls/form_search/$', onlineforms_views.formSearchAutocomplete),
    url(r'^login/$', onlineforms_views.login, name='login'),
    url(r'^bulk$', onlineforms_views.bulk_assign, name='bulk_assign'),
    url(r'^participated/$', onlineforms_views.participated_in, name='participated_in'),
    url(r'^view/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/$', onlineforms_views.view_submission, name='view_submission'),
    url(r'^view/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/re-open$', onlineforms_views.reopen_submission, name='reopen_submission'),
    url(r'^view/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/' + '(?P<action>\w+)/' + '(?P<file_id>\d+)/$', onlineforms_views.file_field_download, name='file_field_download'),
    url(r'^view/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/' + '(?P<action>\w+)/' + '(?P<file_id>\d+)/(?P<secret>\w+)$', onlineforms_views.file_field_download_unauth, name='file_field_download_unauth'),
    url(r'^' + FORM_SLUG + '/$', onlineforms_views.sheet_submission_initial, name='sheet_submission_initial'),
    url(r'^' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/' + SHEET_SLUG + '/' + SHEETSUBMIT_SLUG + '$', onlineforms_views.sheet_submission_subsequent, name='sheet_submission_subsequent'),
    url(r'^submission/' + SECRET_SUBMIT_URL + '/$', onlineforms_views.sheet_submission_via_url, name='sheet_submission_via_url'),
    url(r'^' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/' + SHEET_SLUG + '/' + SHEETSUBMIT_SLUG + '/reject$', onlineforms_views.reject_sheet_subsequent, name='reject_sheet_subsequent'),
    url(r'^' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/' + SHEET_SLUG + '/' + SHEETSUBMIT_SLUG + '/admin_reject$',
        onlineforms_views.reject_sheet_admin, name='reject_sheet_admin'),
    url(r'^submission' + SECRET_SUBMIT_URL + '/' + FORM_SLUG + '/reject_admin$', onlineforms_views.reject_sheet_via_url_admin,
        name='reject_sheet_via_url_admin'),
    url(r'^submission/' + SECRET_SUBMIT_URL + '/reject$', onlineforms_views.reject_sheet_via_url, name='reject_sheet_via_url'),
]
