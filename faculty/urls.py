from django.conf.urls import url
from courselib.urlparts import USERID_OR_EMPLID

faculty_patterns = [
    url(r'^$', 'faculty.views.index'),
    url(r'^summary/' + USERID_OR_EMPLID+ '/$', 'faculty.views.summary'),
]
