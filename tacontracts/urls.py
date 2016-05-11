from django.conf.urls import url
from courselib.urlparts import SLUG_RE, SEMESTER, UNIT_SLUG

CATEGORY_SLUG = '(?P<category_slug>' + SLUG_RE + ')'
CONTRACT_SLUG = '(?P<contract_slug>' + SLUG_RE + ')'
COURSE_SLUG = '(?P<course_slug>' + SLUG_RE + ')'

tacontract_patterns = [ # prefix /tacontract/
    url(r'^$', 'tacontracts.views.list_all_semesters'),
    url(r'^new_semester$', 'tacontracts.views.new_semester'),

    url(r'^student/'+SEMESTER+'$', 'tacontracts.views.student_contract'),
    url(r'^student/'+SEMESTER+'/'+CONTRACT_SLUG+'$', 'tacontracts.views.accept_contract'),

    url(r'^'+SEMESTER+'/setup$', 'tacontracts.views.setup_semester'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/edit$', 'tacontracts.views.edit_semester'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'$', 'tacontracts.views.list_all_contracts'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/course$', 'tacontracts.views.list_all_contracts_by_course'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/new_category$', 'tacontracts.views.new_category'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/category$', 'tacontracts.views.view_categories'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/copy_categories$', 'tacontracts.views.copy_categories'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/csv$', 'tacontracts.views.contracts_csv'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/bulk_email$', 'tacontracts.views.bulk_email'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/category/'+CATEGORY_SLUG+'/edit$', 'tacontracts.views.edit_category'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/category/'+CATEGORY_SLUG+'/delete$', 'tacontracts.views.hide_category'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/new_contract$', 'tacontracts.views.new_contract'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'$', 'tacontracts.views.view_contract'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'/edit$', 'tacontracts.views.edit_contract'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'/sign$', 'tacontracts.views.sign_contract'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'/cancel$', 'tacontracts.views.cancel_contract'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'/copy$', 'tacontracts.views.copy_contract'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'/print$', 'tacontracts.views.print_contract'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'/new_course$', 'tacontracts.views.new_course'),
    url(r'^'+UNIT_SLUG+'/'+SEMESTER+'/contract/'+CONTRACT_SLUG+'/'+COURSE_SLUG+'$', 'tacontracts.views.delete_course'),
]
