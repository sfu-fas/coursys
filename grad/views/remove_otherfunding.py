from django.shortcuts import get_object_or_404
from grad.models import GradStudent, OtherFunding
from django.contrib import messages
from log.models import LogEntry
from courselib.auth import requires_role
from django.http import HttpResponseRedirect
from django.urls import reverse

@requires_role("GRAD")
def remove_otherfunding(request, grad_slug, o_id):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    otherfunding = get_object_or_404(OtherFunding, student=grad, id=o_id)
    if request.method == 'POST':
        otherfunding.removed = True
        otherfunding.save()
        messages.success(request, "Removed other funding %s." % str(otherfunding) )
        l = LogEntry(userid=request.user.username,
              description="Removed otherfunding %s for %s." % (str(otherfunding), grad.person.userid),
              related_object=otherfunding)
        l.save()              
    
    return HttpResponseRedirect(reverse('grad:manage_otherfunding', kwargs={'grad_slug':grad_slug}))
