from django.conf.urls import url
from oauth_provider.urls import urlpatterns as oauth_patterns
from coredata.api_views import my_offerings

api_patterns = [
#    url(r'^confirm/$', confirm_auth),
    url(r'^offerings/$', my_offerings),
]

api_patterns += oauth_patterns