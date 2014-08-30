from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from oauth_provider.urls import urlpatterns as oauth_patterns
from coredata.api_views import MyOfferings

api_patterns = [
    url(r'^offerings$', MyOfferings.as_view()),
]
api_patterns = format_suffix_patterns(api_patterns)

api_patterns += oauth_patterns