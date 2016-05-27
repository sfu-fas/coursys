from django.conf.urls import url
from outreach import views
from courselib.urlparts import SLUG_RE

outreach_pattern = [ # prefix /outreach/
    url('^$', views.index, name='index'),

]
