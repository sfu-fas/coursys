from django.conf.urls import url
from courselib.urlparts import SLUG_RE

CATEGORY_SLUG = '(?P<category_slug>' + SLUG_RE + ')'
CONTRACT_SLUG = '(?P<contract_slug>' + SLUG_RE + ')'
COURSE_SLUG = '(?P<course_slug>' + SLUG_RE + ')'

tacontract_patterns = [ # prefix /tacontract/
    url(r'^$', 'tacontracts.views.list_all_contracts'),
    url(r'^new_category$', 'tacontracts.views.new_category'),
    url(r'^category$', 'tacontracts.views.view_categories'),
    url(r'^category/'+CATEGORY_SLUG+'/edit$', 'tacontracts.views.edit_category'),
    url(r'^category/'+CATEGORY_SLUG+'/delete$', 'tacontracts.views.hide_category'),
    url(r'^new_contract$', 'tacontracts.views.new_contract'),
    url(r'^contract/'+CONTRACT_SLUG+'$', 'tacontracts.views.view_contract'),
    url(r'^contract/'+CONTRACT_SLUG+'/edit$', 'tacontracts.views.edit_contract'),
    url(r'^contract/'+CONTRACT_SLUG+'/sign$', 'tacontracts.views.sign_contract'),
    url(r'^contract/'+CONTRACT_SLUG+'/cancel$', 'tacontracts.views.cancel_contract'),
    url(r'^contract/'+CONTRACT_SLUG+'/copy$', 'tacontracts.views.copy_contract'),
    url(r'^contract/'+CONTRACT_SLUG+'/print$', 'tacontracts.views.print_contract'),
    url(r'^contract/'+CONTRACT_SLUG+'/new_course$', 'tacontracts.views.new_course'),
    url(r'^contract/'+CONTRACT_SLUG+'/'+COURSE_SLUG+'$', 'tacontracts.views.delete_course'),
]
