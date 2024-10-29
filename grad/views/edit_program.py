from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect
from grad.forms import GradProgramForm
from django.urls import reverse
from grad.models import GradProgram

@requires_role("GRAD", get_only=["GRPD"])
def edit_program(request, program_id):
    program = get_object_or_404(GradProgram, id=program_id)
    if request.method == 'POST':
        form = GradProgramForm(request.POST, instance=program)
        form.fields['unit'].disabled=True
        form.fields['label'].disabled=True
        if form.is_valid():
            form.save()
            messages.success(request, "Edited program %s for %s." % (form.instance.label, form.instance.unit))
            l = LogEntry(userid=request.user.username,
                  description="Edited program %s for %s." % (form.instance.label, form.instance.unit),
                  related_object=form.instance)
            l.save()                        
            return HttpResponseRedirect(reverse('grad:programs'))
    else:
        form = GradProgramForm(instance=program)
        form.fields['unit'].disabled=True
        form.fields['label'].disabled=True  

    page_title = 'Edit Program'  
    crumb = 'Edit Program' 
    context = {
               'form': form,
               'page_title' : page_title,
               'crumb' : crumb,
               'program': program,
               }
    return render(request, 'grad/edit_program.html', context)