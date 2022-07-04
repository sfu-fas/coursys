from django.urls import re_path as url
from courselib.urlparts import SLUG_RE, SEMESTER, UNIT_SLUG, ID_RE
import tacontracts.views as tacontracts_views

CATEGORY_SLUG = '(?P<category_slug>' + SLUG_RE + ')'
CONTRACT_SLUG = '(?P<contract_slug>' + SLUG_RE + ')'
COURSE_SLUG = '(?P<course_slug>' + SLUG_RE + ')'
DESCRIPTION_ID = '(?P<description_id>' + ID_RE + ')'
ATTACH_SLUG = '(?P<attach_slug>' + SLUG_RE + ')'



tacontract_patterns = [ # prefix /tacontract/
    url(r'^$', tacontracts_views.list_all_semesters, name='list_all_semesters'),
    url(r'^descriptions/$', tacontracts_views.descriptions, name='descriptions'),
    url(r'^descriptions/new$', tacontracts_views.new_description, name='new_description'),
    url(r'^description/' + DESCRIPTION_ID + '/edit$', tacontracts_views.edit_description, name='edit_description'),
    url(r'^description/' + DESCRIPTION_ID + '/delete$', tacontracts_views.delete_description,
        name='delete_description'),
    url(r'^new_semester$', tacontracts_views.new_semester, name='new_semester'),

    url(r'^student/'+SEMESTER+'$', tacontracts_views.student_contract, name='student_contract'),
    url(r'^student/'+SEMESTER+'/'+CONTRACT_SLUG+'$', tacontracts_views.accept_contract, name='accept_contract'),
    url(r'^student/'+SEMESTER+'/'+CONTRACT_SLUG+'/reject$', tacontracts_views.reject_contract, name='reject_contract'),
    url(r'^student/'+SEMESTER+'/'+CONTRACT_SLUG+'/print$', tacontracts_views.ta_print_contract, name='ta_print_contract'),

    url(r'^'+SEMESTER+'/setup$', tacontracts_views.setup_semester, name='setup_semester'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/edit$', tacontracts_views.edit_semester, name='edit_semester'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'$', tacontracts_views.list_all_contracts, name='list_all_contracts'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/course$', tacontracts_views.list_all_contracts_by_course, name='list_all_contracts_by_course'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/new_category$', tacontracts_views.new_category, name='new_category'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/category$', tacontracts_views.view_categories, name='view_categories'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/copy_categories$', tacontracts_views.copy_categories, name='copy_categories'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/csv$', tacontracts_views.contracts_csv, name='contracts_csv'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/bulk_email$', tacontracts_views.bulk_email, name='bulk_email'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/financials$', tacontracts_views.view_financial_summary, name='view_financials'),
    url(r'^' + UNIT_SLUG + '/' + SEMESTER + '/download_financials$', tacontracts_views.download_financials,
        name='download_financials'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/category/'+CATEGORY_SLUG+'/edit$', tacontracts_views.edit_category, name='edit_category'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/category/'+CATEGORY_SLUG+'/delete$', tacontracts_views.hide_category, name='hide_category'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contracts$', tacontracts_views.print_all_contracts, name='print_all_contracts'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/new_contract$', tacontracts_views.new_contract, name='new_contract'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'$', tacontracts_views.view_contract, name='view_contract'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'/edit$', tacontracts_views.edit_contract, name='edit_contract'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'/sign$', tacontracts_views.sign_contract, name='sign_contract'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'/cancel$', tacontracts_views.cancel_contract, name='cancel_contract'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'/copy$', tacontracts_views.copy_contract, name='copy_contract'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'/print$', tacontracts_views.print_contract, name='print_contract'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'/new_course$', tacontracts_views.new_course, name='new_course'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'/'+COURSE_SLUG+'/edit_course$', tacontracts_views.edit_course, name='edit_course'),
    url(r'^' + UNIT_SLUG + '/' + SEMESTER + '/contract/' + CONTRACT_SLUG + '/new_attachment$',
        tacontracts_views.new_attachment, name='new_attachment'),
    url(r'^' + UNIT_SLUG + '/' + SEMESTER + '/contract/' + CONTRACT_SLUG + '/view_attachment/' + ATTACH_SLUG,
        tacontracts_views.view_attachment, name='view_attachment'),
    url(r'^' + UNIT_SLUG + '/' + SEMESTER + '/contract/' + CONTRACT_SLUG + '/download_attachment/' + ATTACH_SLUG,
        tacontracts_views.download_attachment, name='download_attachment'),
    url(r'^' + UNIT_SLUG + '/' + SEMESTER + '/contract/' + CONTRACT_SLUG + '/delete_attachment/' + ATTACH_SLUG,
        tacontracts_views.delete_attachment, name='delete_attachment'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'/'+COURSE_SLUG+'$', tacontracts_views.delete_course, name='delete_course'),
]
