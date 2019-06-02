from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from coredata.models import Semester
from grad.models import GradStudent, GradProgram, GradProgramHistory
from grad.forms import GradProgramHistoryForm
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect
from django.urls import reverse

@requires_role("GRAD")
def manage_program(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    programs = GradProgram.objects.filter(unit__in=request.units)
    # If you have access to programs from different units, display them.
    if len(request.units) > 1:
        program_choices = [(p.id, str(p) + " (" + p.unit.label + ")") for p in programs]
    else:
        program_choices = [(p.id, str(p)) for p in programs]
    programhistory = GradProgramHistory.objects.filter(student=grad, program__unit__in=request.units).order_by('starting')
    
    if request.method == 'POST':
        form = GradProgramHistoryForm(request.POST)
        form.fields['program'].choices = program_choices
        if form.is_valid():
            gph = form.save(commit=False)
            gph.student = grad
            gph.save()
            grad.update_status_fields()

            messages.success(request, "Updated program info for %s." % (grad.person))
            l = LogEntry(userid=request.user.username,
                  description="Updated grad program for %s." % (grad),
                  related_object=gph)
            l.save()    
            return HttpResponseRedirect(reverse('grad:view', kwargs={'grad_slug':grad.slug}))
    else:
        form = GradProgramHistoryForm(initial={'program': grad.program, 'semester': Semester.current()})
        form.fields['program'].choices = program_choices

    context = {
               'form': form,
               'grad': grad,
               'programhistory': programhistory,
               }
    return render(request, 'grad/manage_program.html', context)
