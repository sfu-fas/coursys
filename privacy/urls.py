from django.conf.urls import url

privacy_patterns = [ # prefix /privacy/
    url(r'^$', 'privacy.views.privacy', name='privacy')
]
