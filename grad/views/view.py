from courselib.auth import requires_role, NotFoundResponse
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, Supervisor, GradStatus, CompletedRequirement, GradRequirement

@requires_role("GRAD")
def view(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    context = {'grad': grad}
    if 'section' in request.GET:
        # page sections fetched by AJAX calls
        section = request.GET['section']
        if section == 'general':
            return render(request, 'grad/view__general.html', context)
        elif section == 'committee':
            supervisors = Supervisor.objects.filter(student=grad)
            context['supervisors'] = supervisors
            return render(request, 'grad/view__committee.html', context)
        elif section == 'status':
            status_history = GradStatus.objects.filter(student=grad, hidden=False)
            context['status_history'] = status_history
            return render(request, 'grad/view__status.html', context)
        elif section == 'requirements':
            completed_req = CompletedRequirement.objects.filter(student=grad)
            req = GradRequirement.objects.filter(program=grad.program)
            missing_req = req    
            for s in completed_req:
                missing_req = missing_req.exclude(description=s.requirement.description)
            context['completed_req'] = completed_req
            context['missing_req'] = missing_req
            return render(request, 'grad/view__requirements.html', context)
        else:
            return NotFoundResponse(request)
    else:
        return render(request, 'grad/view.html', context)