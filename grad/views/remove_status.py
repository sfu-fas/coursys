from django.shortcuts import get_object_or_404
from grad.models import GradStudent, GradStatus
from django.contrib import messages
from log.models import LogEntry
from courselib.auth import requires_role
from django.http import HttpResponseRedirect
from django.urls import reverse


@requires_role("GRAD")
def remove_status(request, grad_slug, s_id):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    status = get_object_or_404(GradStatus, student=grad, id=s_id)
    if request.method == 'POST':
        status.hidden = True
        status.save()
        messages.success(request, "Hid grad status %s." % str(status) )
        l = LogEntry(userid=request.user.username,
              description="Removed grad status %s for %s." % (str(status), grad.person.userid),
              related_object=status)
        l.save()              
    
    return HttpResponseRedirect(reverse('grad:manage_status', kwargs={'grad_slug':grad_slug}))
