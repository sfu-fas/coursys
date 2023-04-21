from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, LetterTemplate
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect
from grad.forms import LetterForm
import datetime
from django.urls import reverse
from coredata.models import Role

@requires_role("GRAD")
def new_letter(request, grad_slug, letter_template_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)

    template = get_object_or_404(LetterTemplate, slug=letter_template_slug, unit__in=request.units)

    from_choices = [('', '\u2014')] \
                    + [(r.person.id, "%s. %s, %s" %
                            (r.person.get_title(), r.person.letter_name(), r.get_role_display()))
                        for r in Role.objects_fresh.filter(unit=grad.program.unit, role__in=['GRPD','GRAD','TAAD','TADM','FUND','ADMN'])]
    directors = Role.objects.filter(unit=grad.program.unit, role='GRPD').order_by('-id')
    if directors:
        default_from = directors[0].person.id
        default_fromlines = "%s. %s\r\n%s" % (directors[0].person.get_title(), directors[0].person.letter_name(), 'Graduate Program Director')
    else:
        default_from = None
        default_fromlines = None
    
    ls = grad.letter_info()
    if request.method == 'POST':
        form = LetterForm(request.POST)
        form.fields['from_person'].choices = from_choices
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = request.user.username
            f.config.update(ls)
            f.template = template;
            f.save()
            messages.success(request, "Created new %s letter for %s." % (form.instance.template.label, form.instance.student))
            l = LogEntry(userid=request.user.username,
                  description="Created new %s letter for %s." % (form.instance.template.label, form.instance.student),
                  related_object=form.instance)
            l.save()            
            return HttpResponseRedirect(reverse('grad:manage_letters', kwargs={'grad_slug':grad_slug}))
    else:
        form = LetterForm(initial={'student': grad, 'date': datetime.date.today(), 'from_person': default_from, 'from_lines': default_fromlines})
        form.fields['from_person'].choices = from_choices
        
    context = {
               'form': form,
               'grad' : grad,
               'template' : template
               }
    return render(request, 'grad/new_letter.html', context)

