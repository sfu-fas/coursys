from courselib.auth import requires_role
from django.shortcuts import render
from grad.models import GradStudent, STATUS_ACTIVE
from grad.views.add_supervisors import _get_grads_missing_supervisors

@requires_role("GRAD", get_only=["GRPD"])
def active_students(request):
    grads = GradStudent.objects.filter(program__unit__in=request.units, current_status__in=STATUS_ACTIVE).select_related('person', 'program').distinct()
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