from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, ExternalDocument
from django.contrib import messages
from django.http import HttpResponseRedirect
from grad.forms import ExternalDocumentForm
from django.urls import reverse
from log.models import LogEntry

@requires_role("GRAD")
def manage_documents(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug = grad_slug)
    documents = ExternalDocument.objects.filter(student=grad).order_by('date')
    
    if request.method == 'POST':
        form = ExternalDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.student = grad
            if 'file_attachment' in request.FILES:
                upfile = request.FILES['file_attachment']
                document.file_mediatype = upfile.content_type
            document.save()
            messages.success(request, 
                             "Document for %s sucessfully saved." % (grad))
            l = LogEntry(userid=request.user.username, 
              description="added document for %s" % (grad.slug,),
              related_object=document )
            l.save()
            
            return HttpResponseRedirect(reverse('grad:manage_documents', 
                                                kwargs={'grad_slug':grad.slug}))
    else:
        form = ExternalDocumentForm()
    
    context = {
                'grad':grad,
                'form': form,
                'documents': documents,
                'can_edit': True,
              }
    return render(request, 'grad/manage_documents.html', context)

