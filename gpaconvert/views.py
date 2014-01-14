from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import render, get_object_or_404

from gpaconvert.models import GradeSource, DiscreteRule, ContinuousRule
from gpaconvert.models import GradeSource
from gpaconvert.utils import render_to

# admin interface views


# student-facing views
@render_to('gpaconvert/grade_source_list.html')
def list_grade_sources(request):
    grade_sources = GradeSource.objects.filter(status='ACTI')

    return {
        'grade_sources': grade_sources,
    }

