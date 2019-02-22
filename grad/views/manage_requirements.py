from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from coredata.models import Semester
from grad.models import GradStudent, CompletedRequirement, GradRequirement
from grad.forms import CompletedRequirementForm
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect
from django.urls import reverse

@requires_role("GRAD")
def manage_requirements(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)    
    
    # find completed/missing requirements
    completed_req = CompletedRequirement.objects.filter(student=grad)
    completed_gradreq_id = [cr.requirement_id for cr in completed_req if cr.removed==False]
    req = GradRequirement.objects.filter(program=grad.program, hidden=False)
    missing_req = req.exclude(id__in=completed_gradreq_id)
    req_choices = [('', '\u2014')] + [(r.id, r.description) for r in missing_req]
    
    if request.method == 'POST':
        form = CompletedRequirementForm(request.POST)
        form.fields['requirement'].choices = req_choices
        if form.is_valid():
            req = form.save(commit=False)
            req.student = grad
            req.save()
            messages.success(request, "Completed requirement for %s sucessfully saved." % (grad))
            l = LogEntry(userid=request.user.username, 
              description="added completed requirement of %s for %s" % (req.requirement.description, grad.slug),
              related_object=req )
            l.save()
            
            return HttpResponseRedirect(reverse('grad:manage_requirements', kwargs={'grad_slug':grad.slug}))
    else:
        form = CompletedRequirementForm(initial={'student':grad, 'semester':Semester.get_semester()})
        form.fields['requirement'].choices = req_choices
    
    context = {
                'grad':grad,
                'form': form,
                'completed_req': completed_req,
                'missing_req': missing_req,
                'can_edit': True,
              }
    return render(request, 'grad/manage_requirements.html', context)


