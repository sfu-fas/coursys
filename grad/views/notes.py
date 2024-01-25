from django.http import HttpResponseRedirect
from django.urls import reverse
from courselib.auth import requires_role, ForbiddenResponse
from grad.forms import GradNotesForm
from grad.models import GradStudent
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from log.models import LogEntry


@requires_role("GRAD")
def update_note(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    if request.method == 'POST':
        form = GradNotesForm(request.POST)
        if form.is_valid():
            grad.set_notes(form.cleaned_data['notes'])
            grad.save()
            l = LogEntry(userid=request.user.username,
                         description=("Grad notes updated for %s") % grad,
                         related_object=grad)
            l.save()
            messages.add_message(request, messages.SUCCESS,'Grad notes updated.')
            return HttpResponseRedirect(reverse('grad:view', kwargs={'grad_slug': grad.slug}))
    else:
        form = GradNotesForm(instance=grad)
    return render(request, 'grad/update_note.html', {'form': form, 'grad': grad})
    