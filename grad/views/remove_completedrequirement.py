from django.shortcuts import get_object_or_404
from grad.models import GradStudent, CompletedRequirement
from django.contrib import messages
from log.models import LogEntry
from courselib.auth import requires_role
from django.http import HttpResponseRedirect
from django.urls import reverse

@requires_role("GRAD")
def remove_completedrequirement(request, grad_slug, cr_id):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    cr = get_object_or_404(CompletedRequirement, student=grad, id=cr_id)
    if request.method == 'POST':
        cr.removed = True
        cr.save()
        messages.success(request, "Removed completed requirement %s." % (cr.requirement.description))
        l = LogEntry(userid=request.user.username,
              description="Removed completed requirement %s for %s." % (cr.requirement.description, grad.person.userid),
              related_object=cr)
        l.save()              
    
    return HttpResponseRedirect(reverse('grad:manage_requirements', kwargs={'grad_slug':grad_slug}))
