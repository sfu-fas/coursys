from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, LetterTemplate, Letter
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect, HttpResponse
from grad.forms import LetterForm
import datetime
from django.core.urlresolvers import reverse
from view_all_letters import view_all_letters
from coredata.models import Role

@requires_role("GRAD")
def copy_letter(request, grad_slug, letter_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    old_letter = get_object_or_404(Letter, slug=letter_slug, student=grad)
    letter = Letter(student=grad, to_lines=old_letter.to_lines, content=old_letter.content, template=old_letter.template,
                    salutation=old_letter.salutation, closing=old_letter.closing, from_person=old_letter.from_person,
                    from_lines=old_letter.from_lines)
    
    templates = LetterTemplate.objects.filter(unit=grad.program.unit)
    from_choices = [('', u'\u2014')] + [(r.person.id, "%s, %s" % (r.person.name(), r.get_role_display()))
                                        for r in Role.objects.filter(unit=grad.program.unit)]
    
    if request.method == 'POST':
        form = LetterForm(request.POST, instance=letter)
        form.fields['from_person'].choices = from_choices
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = request.user.username
            f.config = grad.letter_info()
            f.save()
            messages.success(request, "Created new %s letter for %s." % (form.instance.template.label, form.instance.student))
            l = LogEntry(userid=request.user.username,
                  description="Created new %s letter for %s." % (form.instance.template.label, form.instance.student),
                  related_object=form.instance)
            l.save()            
            return HttpResponseRedirect(reverse(view_all_letters, kwargs={'grad_slug':grad_slug}))
    else:
        form = LetterForm(instance=letter, initial={'date': datetime.date.today()})
        form.fields['from_person'].choices = from_choices
        
    context = {
               'form': form,
               'grad' : grad,
               'templates' : templates,
               'letter': letter,
               }
    return render(request, 'grad/copy_letter.html', context)

