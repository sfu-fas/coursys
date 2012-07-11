from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, Supervisor, GradRequirement, \
    CompletedRequirement, GradStatus, Letter

@requires_role("GRAD")
def view_all(request, grad_slug):
    # will display academic, personal, FIN, status history, supervisor
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    supervisors = Supervisor.objects.filter(student=grad, removed=False)
    status_history = GradStatus.objects.filter(student=grad, hidden=False)
    letter = Letter.objects.filter(student=grad)
    
    #calculate missing reqs
    completed_req = CompletedRequirement.objects.filter(student=grad)
    req = GradRequirement.objects.filter(program=grad.program)
    missing_req = req    
    for s in completed_req:
        missing_req = missing_req.exclude(description=s.requirement.description)
    
    # set frontend defaults
    gp = grad.person.get_fields
    context = {
               'grad' : grad,
               'gp' : gp,
               'status_history' : status_history,
               'supervisors' : supervisors,
               'completed_req' : completed_req,
               'missing_req' : missing_req,
               'letter' : letter         
               }
    return render(request, 'grad/view_all.html', context)
