#!/usr/bin/env python

from django.conf.urls.defaults import *
#from courses.urls import COURSE_SLUG_RE

COURSE_SLUG_RE = '\d{4}-[a-z]{2,4}-\w{3,4}-[a-z]\d{3}'
urlpatterns = patterns('',
    url(r'^$', 'grades.views.index'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/addnumericactivity$', 'grades.views.add_numeric_activity'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/addletteractivity$', 'grades.views.add_letter_activity'),
    url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')$', 'grades.views.course'),
    #url(r'^instructor$', 'grades.views.instructor_view'),
    url(r'^student$', 'grades.views.student_view'),
    url(r'^student/'+'(?P<course_slug>'+ COURSE_SLUG_RE + ')$', 'grades.views.student_grade'),
)
