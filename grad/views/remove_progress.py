from django.shortcuts import get_object_or_404
from grad.models import GradStudent, ProgressReport
from django.contrib import messages
from log.models import LogEntry
from courselib.auth import requires_role
from django.http import HttpResponseRedirect
from django.urls import reverse

@requires_role("GRAD")
def remove_progress(request, grad_slug, p_id):
    grad = get_object_or_404(GradStudent, slug=grad_slug, 
                             program__unit__in=request.units)
    progress = get_object_or_404(ProgressReport, student=grad, id=p_id)
    if request.method == 'POST':
        progress.removed = True
        progress.save()
        messages.success(request, 
                         "Removed progress report %s." % (str(progress),) )
        l = LogEntry(userid=request.user.username,
                     description="Removed progress report %s for %s." % 
                                 (str(progress), grad.person.userid),
                     related_object=progress)
        l.save()              
    
    return HttpResponseRedirect(reverse('grad:manage_progress', 
                                kwargs={'grad_slug':grad_slug}))
