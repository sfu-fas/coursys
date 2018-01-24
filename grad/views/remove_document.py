from django.shortcuts import get_object_or_404
from grad.models import GradStudent, ExternalDocument
from django.contrib import messages
from log.models import LogEntry
from courselib.auth import requires_role
from django.http import HttpResponseRedirect
from django.urls import reverse

@requires_role("GRAD")
def remove_document(request, grad_slug, d_id):
    grad = get_object_or_404(GradStudent, slug=grad_slug, 
                             program__unit__in=request.units)
    document = get_object_or_404(ExternalDocument, student=grad, id=d_id)
    if request.method == 'POST':
        document.removed = True
        document.save()
        messages.success(request, 
                         "Removed document %s." % (str(document),) )
        l = LogEntry(userid=request.user.username,
                     description="Removed document %s for %s." % 
                                 (str(document), grad.person.userid),
                     related_object=document)
        l.save()              
    
    return HttpResponseRedirect(reverse('grad:manage_documents', 
                                kwargs={'grad_slug':grad_slug}))
