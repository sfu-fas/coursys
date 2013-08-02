from django.conf.urls.defaults import patterns, url
from courselib.urlparts import USERID_OR_EMPLID, SLUG_RE

FORM_SLUG = '(?P<form_slug>' + SLUG_RE + ')'
SHEET_SLUG = '(?P<sheet_slug>' + SLUG_RE + ')'
FIELD_SLUG = '(?P<field_slug>' + SLUG_RE + ')'
FORMSUBMIT_SLUG = '(?P<formsubmit_slug>' + SLUG_RE + ')'
SHEETSUBMIT_SLUG = '(?P<sheetsubmit_slug>' + SLUG_RE + ')'
FORMGROUP_SLUG = '(?P<formgroup_slug>' + SLUG_RE + ')'
SECRET_SUBMIT_URL = '(?P<secret_url>' + SLUG_RE + ')'

urlpatterns = patterns('',
    url(r'^groups/$', 'onlineforms.views.manage_groups'),
    url(r'^groups/new$', 'onlineforms.views.new_group'),
    url(r'^groups/' + FORMGROUP_SLUG + '/$', 'onlineforms.views.manage_group'),
    url(r'^groups/' + FORMGROUP_SLUG + '/add$', 'onlineforms.views.add_group_member'),
    url(r'^groups/' + FORMGROUP_SLUG + '/remove/' + USERID_OR_EMPLID + '/$', 'onlineforms.views.remove_group_member'),

    url(r'^admin/$', 'onlineforms.views.admin_list_all'),
    url(r'^admin/assign$', 'onlineforms.views.admin_assign_any'),
    url(r'^admin/assign-nonsfu$', 'onlineforms.views.admin_assign_any_nonsfu'),
    url(r'^admin/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/assign$', 'onlineforms.views.admin_assign'),
    url(r'^admin/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/assign-nonsfu$', 'onlineforms.views.admin_assign_nonsfu'),
    url(r'^admin/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/assign_done$', 'onlineforms.views.admin_done'),
    
    url(r'^manage/$', 'onlineforms.views.list_all'),
    url(r'^manage/new$', 'onlineforms.views.new_form'),
    url(r'^manage/' + FORM_SLUG + '/$', 'onlineforms.views.view_form'),
    url(r'^manage/' + FORM_SLUG + '/edit$', 'onlineforms.views.edit_form'),
    url(r'^manage/' + FORM_SLUG + '/new$', 'onlineforms.views.new_sheet'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/preview$', 'onlineforms.views.preview_sheet'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/$', 'onlineforms.views.edit_sheet'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/edit$', 'onlineforms.views.edit_sheet_info'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/reorder$', 'onlineforms.views.reorder_field'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/new$', 'onlineforms.views.new_field'),
    url(r'^manage/' + FORM_SLUG + '/edit/' + SHEET_SLUG + '/field-' + FIELD_SLUG + '$', 'onlineforms.views.edit_field'),

    url(r'^$', 'onlineforms.views.index'),
    url(r'^view/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/$', 'onlineforms.views.view_submission'),
    url(r'^view/' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/' + '(?P<sheet_id>\d+)/'+ '(?P<disposition>\w+)/' + '(?P<file_id>\d+)/$', 'onlineforms.views.file_field_download'),
    url(r'^submission/' + SECRET_SUBMIT_URL + '/$', 'onlineforms.views.sheet_submission_via_url'),
    url(r'^' + FORM_SLUG + '/$', 'onlineforms.views.sheet_submission'),
    url(r'^' + FORM_SLUG + '/' + FORMSUBMIT_SLUG + '/' + SHEET_SLUG + '/' + SHEETSUBMIT_SLUG + '$', 'onlineforms.views.sheet_submission'),
)
