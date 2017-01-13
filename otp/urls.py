from django.conf.urls import url
from . import views

twofactor_patterns = [
    url(r'^login/$', views.login_2fa, name='login_2fa'),
]