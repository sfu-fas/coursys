from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import LetterTemplate, LETTER_TAGS
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect, HttpResponse
from grad.forms import LetterTemplateForm
from django.core.urlresolvers import reverse
from .letter_templates import letter_templates

@requires_role("GRAD", get_only=["GRPD"])
def manage_letter_template(request, letter_template_slug):
    unit_choices = [(u.id, u.name) for u in request.units]    
    letter_template = get_object_or_404(LetterTemplate, slug=letter_template_slug)
    if request.method == 'POST':
        form = LetterTemplateForm(request.POST, instance=letter_template)
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = request.user.username            
            f.save()
            messages.success(request, "Updated %s letter for %s." % (form.instance.label, form.instance.unit))
            l = LogEntry(userid=request.user.username,
                  description="Updated new %s letter for %s." % (form.instance.label, form.instance.unit),
                  related_object=form.instance)
            l.save()            
            return HttpResponseRedirect(reverse('grad:letter_templates'))
    else:
        form = LetterTemplateForm(instance=letter_template)
        form.fields['unit'].choices = unit_choices 

    page_title = 'Manage Letter Template'  
    crumb = 'Manage' 
    lt = sorted(LETTER_TAGS.items())
    context = {
               'form': form,
               'page_title' : page_title,
               'crumb' : crumb,
               'letter_template' : letter_template,
               'LETTER_TAGS' : lt
               }
    return render(request, 'grad/manage_letter_template.html', context)
