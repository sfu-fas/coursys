from django.shortcuts import get_object_or_404

from gpaconvert.forms import DiscreteGradeForm
from gpaconvert.models import GradeSource
from gpaconvert.utils import render_to


@render_to('gpaconvert/grade_source_list.html')
def list_grade_sources(request):
    grade_sources = GradeSource.objects.filter(status='ACTI')

    return {
        'grade_sources': grade_sources,
    }


@render_to('gpaconvert/convert_grades_form.html')
def convert_grades(request, grade_source_slug):
    grade_source = get_object_or_404(GradeSource, slug=grade_source_slug)

    if request.POST:
        form = DiscreteGradeForm(request.POST, grade_source=grade_source)
    else:
        form = DiscreteGradeForm(grade_source=grade_source)

    return {
        'grade_source': grade_source,
        'form': form,
    }
