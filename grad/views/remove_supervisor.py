from django.shortcuts import get_object_or_404
from grad.models import GradStudent, Supervisor
from django.contrib import messages
from log.models import LogEntry
from courselib.auth import requires_role
from django.http import HttpResponseRedirect
from django.urls import reverse

@requires_role("GRAD")
def remove_supervisor(request, grad_slug, sup_id):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    supervisor = get_object_or_404(Supervisor, student=grad, id=sup_id)
    if request.method == 'POST':
        supervisor.removed = True
        supervisor.save()
        messages.success(request, "Removed committe member %s." % (supervisor.supervisor or supervisor.external))
        l = LogEntry(userid=request.user.username,
              description="Removed committee member %s for %s." % (supervisor.supervisor or supervisor.external, grad.person.userid),
              related_object=supervisor)
        l.save()              
    
    return HttpResponseRedirect(reverse('grad:manage_supervisors', kwargs={'grad_slug':grad_slug}))
