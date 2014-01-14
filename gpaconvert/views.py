import functools

from django.forms.formsets import formset_factory
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

    # XXX: This is required because our form class requires a GradeSource.
    RuleFormSet = formset_factory(RuleForm, extra=10)
    RuleFormSet.form = functools.partial(RuleForm, grade_source=grade_source)

    # TODO: Figure out a better way to handle the transfer grades.
    if request.POST:
        formset = RuleFormSet(request.POST)
        if formset.is_valid():
            transfer_grades = [form.cleaned_data['rule'].transfer_value
                               if 'rule' in form.cleaned_data else ''
                               for form in formset]
        else:
            transfer_grades = ['' for _ in xrange(len(formset))]
    else:
        formset = RuleFormSet()
        transfer_grades = ['' for _ in xrange(len(formset))]

    return {
        'grade_source': grade_source,
        'formset': formset,
        'transfer_grades': iter(transfer_grades),
    }
