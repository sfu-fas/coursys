from django.urls import re_path as url
from courselib.urlparts import SLUG_RE
from . import views

REMINDER_SLUG = '(?P<reminder_slug>' + SLUG_RE + ')'

reminders_patterns = [
    url(r'^$', views.index, name='index'),
    url(r'^create$', views.create, name='create'),
    url(r'^' + REMINDER_SLUG + '/$', views.view, name='view'),
    url(r'^' + REMINDER_SLUG + '/edit$', views.edit, name='edit'),
    url(r'^' + REMINDER_SLUG + '/delete', views.delete, name='delete'),
]