from django.conf.urls import url
from courselib.urlparts import SLUG_RE, ID_RE
from space import views


SPACE_SLUG = '(?P<space_slug>' + SLUG_RE + ')'

space_patterns = [  # prefix /space/

]
