from django.urls import re_path as url
import privacy.views as privacy_views

privacy_patterns = [ # prefix /privacy/
    url(r'^$', privacy_views.privacy, name='privacy'),
    url(r'^da/$', privacy_views.privacy_da, name='privacy_da')
]
