from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, LetterTemplate
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect, HttpResponse
from grad.forms import LetterForm
import datetime
from django.core.urlresolvers import reverse
from view_all_letters import view_all_letters
from coredata.models import Role

@requires_role("GRAD")
def new_letter(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    templates = LetterTemplate.objects.filter(unit=grad.program.unit)
    from_choices = [('', u'\u2014')] + [(r.person.id, "%s, %s" % (r.person.name(), r.get_role_display()))
                                        for r in Role.objects.filter(unit=grad.program.unit)]
    directors = Role.objects.filter(unit=grad.program.unit, role='GRPD').order_by('-id')
    if directors:
        default_from = directors[0].person.id
    else:
        default_from = None
    
    ls = grad.letter_info()
    if request.method == 'POST':
        form = LetterForm(request.POST)
        form.fields['from_person'].choices = from_choices
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = request.user.username
            f.config = ls
            f.save()
            messages.success(request, "Created new %s letter for %s." % (form.instance.template.label, form.instance.student))
            l = LogEntry(userid=request.user.username,
                  description="Created new %s letter for %s." % (form.instance.template.label, form.instance.student),
                  related_object=form.instance)
            l.save()            
            return HttpResponseRedirect(reverse(view_all_letters, kwargs={'grad_slug':grad_slug}))
    else:
        form = LetterForm(initial={'student': grad, 'date': datetime.date.today(), 'from_person': default_from})
        form.fields['from_person'].choices = from_choices
        
    context = {
               'form': form,
               'grad' : grad,
               'templates' : templates
               }
    return render(request, 'grad/new_letter.html', context)

