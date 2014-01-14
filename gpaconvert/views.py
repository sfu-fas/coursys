from django.shortcuts import get_object_or_404

from gpaconvert.forms import ContinuousGradeForm, DiscreteGradeForm
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
    RuleForm = (grade_source.scale == 'DISC') and DiscreteGradeForm or ContinuousGradeForm
    transfer_grade = ''

    if request.POST:
        form = RuleForm(request.POST, grade_source=grade_source)
        if form.is_valid():
            transfer_grade = form.cleaned_data['rule'].transfer_value
    else:
        form = RuleForm(grade_source=grade_source)

    return {
        'grade_source': grade_source,
        'form': form,
        'transfer_grade': transfer_grade,
    }
