from django.conf.urls import url
from courselib.urlparts import SLUG_RE, ID_RE
import relationships.views as rel_views

CONTACT_SLUG = '(?P<contact_slug>' + SLUG_RE + ')'

relationship_patterns = [ # prefix /relationships/
    url(r'^$', rel_views.index, name='index'),
    url(r'^' + CONTACT_SLUG + '/', rel_views.view_contact, name='view_contact'),
]