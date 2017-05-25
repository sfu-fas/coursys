from django.conf.urls import url
from courselib.urlparts import SLUG_RE, ID_RE
import relationships.views as rel_views

CONTACT_SLUG = '(?P<contact_slug>' + SLUG_RE + ')'

relationship_patterns = [ # prefix /relationships/
    url(r'^$', rel_views.index, name='index'),
    url(r'^new_contact$', rel_views.new_contact, name='new_contact'),
    url(r'^' + CONTACT_SLUG + '/view', rel_views.view_contact, name='view_contact'),
    url(r'^' + CONTACT_SLUG + '/edit$', rel_views.edit_contact, name='edit_contact'),
    url(r'^' + CONTACT_SLUG + '/delete$', rel_views.delete_contact, name='delete_contact'),
]