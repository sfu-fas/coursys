from courselib.auth import requires_role
from django.shortcuts import render
from grad.models import LETTER_TAGS
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect
from grad.forms import LetterTemplateForm
from django.urls import reverse


@requires_role(["GRAD", "GRPD"])
def new_letter_template(request):
    unit_choices = [(u.id, u.name) for u in request.units]
    if request.method == 'POST':
        form = LetterTemplateForm(request.POST)
        form.fields['unit'].choices = unit_choices 
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = request.user.username            
            f.save()
            messages.success(request, "Created new letter template %s for %s." % (form.instance.label, form.instance.unit))
            l = LogEntry(userid=request.user.username,
                  description="Created new letter template %s for %s." % (form.instance.label, form.instance.unit),
                  related_object=form.instance)
            l.save()            
            return HttpResponseRedirect(reverse('grad:letter_templates'))
    else:
        form = LetterTemplateForm()
        form.fields['unit'].choices = unit_choices 

    page_title = 'New Letter Template'  
    crumb = 'New'
    lt = sorted(LETTER_TAGS.items()) 
    context = {
               'form': form,
               'page_title' : page_title,
               'crumb' : crumb,
               'LETTER_TAGS' : lt
               }
    return render(request, 'grad/new_letter_template.html', context)
