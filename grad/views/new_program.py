from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect, HttpResponse
from grad.forms import GradProgramForm
import datetime
from django.urls import reverse

@requires_role("GRAD", get_only=["GRPD"])
def new_program(request):
    unit_choices = [(u.id, u.name) for u in request.units]
    if request.method == 'POST':
        form = GradProgramForm(request.POST)
        form.fields['unit'].choices = unit_choices 
        if form.is_valid():
            form.save()
            messages.success(request, "Created new program %s for %s." % (form.instance.label, form.instance.unit))
            l = LogEntry(userid=request.user.username,
                  description="Created new program %s for %s." % (form.instance.label, form.instance.unit),
                  related_object=form.instance)
            l.save()                        
            return HttpResponseRedirect(reverse('grad:programs'))
    else:
        form = GradProgramForm()    
        form.fields['unit'].choices = unit_choices

    page_title = 'New Program'  
    crumb = 'New Program' 
    context = {
               'form': form,
               'page_title' : page_title,
               'crumb' : crumb
               }
    return render(request, 'grad/new_program.html', context)
