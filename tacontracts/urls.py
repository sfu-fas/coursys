from django.conf.urls import url
from courselib.urlparts import SLUG_RE

CATEGORY_SLUG = '(?P<category_slug>' + SLUG_RE + ')'
CONTRACT_SLUG = '(?P<contract_slug>' + SLUG_RE + ')'

tacontract_patterns = [ # prefix /tacontract/
    url(r'^$', 'tacontracts.views.list_all_contracts'),
    url(r'^new_category$', 'tacontracts.views.new_category'),
    url(r'^'+CATEGORY_SLUG+'$', 'tacontracts.views.list_contracts'),
    url(r'^'+CATEGORY_SLUG+'/update$', 'tacontracts.views.update_category'),
    url(r'^'+CATEGORY_SLUG+'/delete$', 'tacontracts.views.hide_category'),
    url(r'^'+CATEGORY_SLUG+'/new_contract$', 'tacontracts.views.new_contract'),
    url(r'^'+CATEGORY_SLUG+'/'+CONTRACT_SLUG+'$', 'tacontracts.views.view_contract'),
    url(r'^'+CATEGORY_SLUG+'/'+CONTRACT_SLUG+'/update$', 'tacontracts.views.update_contract'),
    url(r'^'+CATEGORY_SLUG+'/'+CONTRACT_SLUG+'/cancel$', 'tacontracts.views.cancel_contract'),
    url(r'^'+CATEGORY_SLUG+'/'+CONTRACT_SLUG+'/sign$', 'tacontracts.views.sign_contract'),
]
