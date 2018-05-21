from django.conf.urls import url, include
from django.conf import settings
from courselib.urlparts import SLUG_RE
from . import views

REMINDER_SLUG = '(?P<reminder_slug>' + SLUG_RE + ')'

reminders_patterns = [
    url(r'^$', views.index, name='index'),
    url(r'^create$', views.create, name='create'),
    url(r'^view/' + REMINDER_SLUG, views.view, name='view'),
]