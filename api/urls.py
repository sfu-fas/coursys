from django.conf.urls import patterns, url
from coredata.api_views import my_offerings

api_patterns = [
    url(r'^offerings/$', my_offerings),
]