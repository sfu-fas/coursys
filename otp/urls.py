from django.conf.urls import url
from . import views

otp_patterns = [
    url(r'^login$', views.login_2fa, name='login_2fa'),
    url(r'^add$', views.add_topt, name='add_topt'),
]