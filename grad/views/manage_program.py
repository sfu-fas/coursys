from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from coredata.models import Semester
from grad.models import GradStudent, GradProgram, GradProgramHistory
from grad.forms import GradProgramHistoryForm
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

@requires_role("GRAD")
def manage_program(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    program_choices = [(p.id, unicode(p)) for p in GradProgram.objects.filter(unit__in=request.units)]
    programhistory = GradProgramHistory.objects.filter(student=grad, program__unit__in=request.units)
    
    if request.method == 'POST':
        form = GradProgramHistoryForm(request.POST)
        form.fields['program'].choices = program_choices
        if form.is_valid():
            gph = form.save(commit=False)
            gph.student = grad
            gph.save()
            grad.program = gph.program
            grad.save()

            messages.success(request, "Updated program info for %s." % (grad.person))
            l = LogEntry(userid=request.user.username,
                  description="Updated grad program for %s." % (grad),
                  related_object=gph)
            l.save()    
            return HttpResponseRedirect(reverse('grad.views.view', kwargs={'grad_slug':grad.slug}))
    else:
        form = GradProgramHistoryForm(initial={'program': grad.program, 'semester': Semester.current()})
        form.fields['program'].choices = program_choices

    context = {
               'form': form,
               'grad': grad,
               'programhistory': programhistory,
               }
    return render(request, 'grad/manage_program.html', context)
