from django.shortcuts import get_object_or_404
from grad.models import GradStudent, Promise
from django.contrib import messages
from log.models import LogEntry
from courselib.auth import requires_role
from django.http import HttpResponseRedirect
from django.urls import reverse

@requires_role("GRAD")
def remove_promise(request, grad_slug, p_id):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    promise = get_object_or_404(Promise, student=grad, id=p_id)
    if request.method == 'POST':
        promise.removed = True
        promise.save()
        messages.success(request, "Removed promise %s." % str(promise) )
        l = LogEntry(userid=request.user.username,
              description="Removed promise %s for %s." % (str(promise), grad.person.userid),
              related_object=promise)
        l.save()              
    
    return HttpResponseRedirect(reverse('grad:manage_promises', kwargs={'grad_slug':grad_slug}))
