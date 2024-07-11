from courselib.auth import requires_role
from django.shortcuts import render
from grad.models import GradStudent

@requires_role("GRAD", get_only=["GRPD"])
def index(request):
    grads = GradStudent.objects.filter(program__unit__in=request.units, current_status="ACTI").select_related('person', 'program').distinct()
    masters_grads = grads.filter(program__grad_category="MA")
    doctoral_grads = grads.filter(program__grad_category="DR")
    other_grads = grads.filter(program__grad_category="OT")
    context = {
        'masters_grads': masters_grads,
        'doctoral_grads': doctoral_grads,
        'other_grads': other_grads,
    }
    return render(request, 'grad/index.html', context)

@requires_role("GRAD")
def config(request):
    context = {}
    return render(request, 'grad/config.html', context)

@requires_role("GRAD")
def reports(request):
    context = {}
    return render(request, 'grad/reports.html', context)