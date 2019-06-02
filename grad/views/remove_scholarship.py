from django.shortcuts import get_object_or_404
from grad.models import GradStudent, Scholarship
from django.contrib import messages
from log.models import LogEntry
from courselib.auth import requires_role
from django.http import HttpResponseRedirect
from django.urls import reverse

@requires_role("GRAD")
def remove_scholarship(request, grad_slug, s_id):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    scholarship = get_object_or_404(Scholarship, student=grad, id=s_id)
    if request.method == 'POST':
        scholarship.removed = True
        scholarship.save()
        messages.success(request, "Removed scholarship %s." % str(scholarship) )
        l = LogEntry(userid=request.user.username,
              description="Removed scholarship %s for %s." % (str(scholarship), grad.person.userid),
              related_object=scholarship)
        l.save()              
    
    return HttpResponseRedirect(reverse('grad:manage_scholarships', kwargs={'grad_slug':grad_slug}))


