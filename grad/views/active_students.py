import csv
from datetime import date
from django.http import HttpResponse
from courselib.auth import requires_role
from django.shortcuts import render
from grad.models import GradStudent, STATUS_ACTIVE, CATEGORY_CHOICES
from grad.views.add_supervisors import _get_grads_missing_supervisors


def _active_grads_queryset(request):
    return GradStudent.objects.filter(
        program__unit__in=request.units,
        current_status__in=STATUS_ACTIVE,
    ).select_related('person', 'program', 'program__unit', 'start_semester').distinct()

@requires_role("GRAD", get_only=["GRPD"])
def active_students(request):
    grads = _active_grads_queryset(request)
    masters_grads = grads.filter(program__grad_category="MA")
    doctoral_grads = grads.filter(program__grad_category="DR")
    other_grads = grads.filter(program__grad_category="OT")
    num_grads_missing_supervisors = _get_grads_missing_supervisors(request.units).count()
    context = {
        'masters_grads': masters_grads,
        'doctoral_grads': doctoral_grads,
        'other_grads': other_grads,
        'num_grads_missing_supervisors': num_grads_missing_supervisors
    }
    return render(request, 'grad/active_students.html', context)


@requires_role("GRAD", get_only=["GRPD"])
def download_active_students(request):
    response = HttpResponse(content_type='text/csv')
    today = date.today().strftime('%m-%d-%Y')
    response['Content-Disposition'] = 'attachment; filename="active-grad-students-%s.csv"' % today
    writer = csv.writer(response)
    writer.writerow([
        'Name',
        'Student ID',
        'Program',
        'Start Semester',
        'Active Terms',
        'Expected Completion Terms',
        'Requirements Completed',
        'Requirements Total',
        'Senior Supervisor',
        'Graduate Category',
    ])

    grads = _active_grads_queryset(request).order_by('program__grad_category', 'person__last_name', 'person__first_name', 'person__emplid')
    graduate_categories = dict(CATEGORY_CHOICES)

    for grad in grads:
        if grad.start_semester:
            start_semester = '%s (%s)' % (grad.start_semester.name, grad.start_semester.label())
        else:
            start_semester = ''

        writer.writerow([
            grad.person.name(),
            grad.person.emplid,
            '%s, %s' % (grad.program.unit.label, grad.program.label),
            start_semester,
            grad.active_semesters()[0],
            grad.program.expected_completion_terms,
            grad.num_completed_requirements(),
            grad.program.num_grad_requirements(),
            grad.list_supervisors(),
            graduate_categories.get(grad.program.grad_category, 'Other'),
        ])

    return response