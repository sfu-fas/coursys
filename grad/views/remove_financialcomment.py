from django.shortcuts import get_object_or_404
from grad.models import GradStudent, FinancialComment
from django.contrib import messages
from log.models import LogEntry
from courselib.auth import requires_role
from django.http import HttpResponseRedirect
from django.urls import reverse

@requires_role("GRAD", get_only=["GRPD"])
def remove_financialcomment(request, grad_slug, f_id):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    fin = get_object_or_404(FinancialComment, student=grad, id=f_id)
    if request.method == 'POST':
        fin.removed = True
        fin.save()
        messages.success(request, "Removed financial comment %s." % str(fin))
        l = LogEntry(userid=request.user.username,
              description="Removed financial comment %s for %s." % (str(fin), grad.person.userid),
              related_object=fin)
        l.save()              
    
    return HttpResponseRedirect(reverse('grad:manage_financialcomments', kwargs={'grad_slug':grad_slug}))
