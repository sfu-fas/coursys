from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, Letter
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect
from grad.forms import LetterForm
import datetime
from django.urls import reverse
from coredata.models import Role

@requires_role("GRAD")
def copy_letter(request, grad_slug, letter_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    old_letter = get_object_or_404(Letter, slug=letter_slug, student=grad)
    letter = Letter(student=grad, to_lines=old_letter.to_lines, content=old_letter.content, template=old_letter.template,
                    closing=old_letter.closing, from_person=old_letter.from_person,
                    from_lines=old_letter.from_lines)
    letter.set_use_sig(old_letter.use_sig())

    from_choices = [('', '\u2014')] \
                    + [(r.person.id, "%s. %s, %s" %
                            (r.person.get_title(), r.person.letter_name(), r.get_role_display()))
                        for r in Role.objects_fresh.filter(unit=grad.program.unit)]
    
    if request.method == 'POST':
        form = LetterForm(request.POST, instance=letter)
        form.fields['from_person'].choices = from_choices
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = request.user.username
            f.config = grad.letter_info()
            f.save()
            messages.success(request, "Created %s letter for %s." % (form.instance.template.label, form.instance.student))
            l = LogEntry(userid=request.user.username,
                  description="Copied %s letter for %s." % (form.instance.template.label, form.instance.student),
                  related_object=form.instance)
            l.save()            
            return HttpResponseRedirect(reverse('grad:manage_letters', kwargs={'grad_slug':grad_slug}))
    else:
        form = LetterForm(instance=letter, initial={'date': datetime.date.today()})
        form.fields['from_person'].choices = from_choices
        
    context = {
               'form': form,
               'grad' : grad,
               'letter': letter,
               }
    return render(request, 'grad/copy_letter.html', context)

