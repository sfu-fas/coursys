#!/usr/bin/env python

from django.conf.urls.defaults import *
from courselib.urlparts import *

urlpatterns = patterns('',
    #url(r'^$', 'grades.views.index'),
    #url(r'^' + COURSE_SLUG + '/addnumericactivity$', 'grades.views.add_numeric_activity'),
    #url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')/addletteractivity$', 'grades.views.add_letter_activity'),
    #url(r'^(?P<course_slug>' + COURSE_SLUG_RE + ')$', 'grades.views.course_info'),
    #url(r'^instructor$', 'grades.views.instructor_view'),
    url(r'^student$', 'grades.views.student_view'),
    url(r'^student/'+'(?P<course_slug>'+ COURSE_SLUG_RE + ')$', 'grades.views.student_grade'),
)
