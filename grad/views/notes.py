from django.http import HttpResponseRedirect
from django.urls import reverse
from courselib.auth import requires_role, ForbiddenResponse
from grad.forms import GradNotesForm
from grad.models import GradStudent
from django.shortcuts import render, get_object_or_404


@requires_role("GRAD")
def add_note(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    if request.method == 'POST':
        form = GradNotesForm(request.POST)
        if form.is_valid():
            grad.set_notes(form.cleaned_data['notes'])
            grad.save()
            return HttpResponseRedirect(reverse('grad:view', kwargs={'grad_slug': grad.slug}))
    else:
        form = GradNotesForm()
    return render(request, 'grad/add_note.html', {'form': form, 'grad': grad})


@requires_role("GRAD")
def delete_note(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    grad.set_notes('')
    grad.save()
    return HttpResponseRedirect(reverse('grad:view', kwargs={'grad_slug': grad.slug}))
