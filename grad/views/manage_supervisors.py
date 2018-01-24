from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, Supervisor, GradRequirement
from grad.forms import SupervisorForm, possible_supervisors
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect
from django.urls import reverse

@requires_role("GRAD")
def manage_supervisors(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    supervisors = Supervisor.objects.filter(student=grad).select_related('supervisor')
    supervisor_people = [s.supervisor for s in supervisors if s.supervisor]

    if request.method == 'POST':
        form = SupervisorForm(request.POST)
        form.set_supervisor_choices(possible_supervisors([grad.program.unit], extras=supervisor_people, null=True))
        if form.is_valid():
            s = form.save(commit=False)
            s.modified_by = request.user.username
            s.student = grad
            s.save()
            
            messages.success(request, "Added committee member for %s." % (grad))
            l = LogEntry(userid=request.user.username,
                  description="Added committee member %s for %s." % (s, grad.person.userid),
                  related_object=s)
            l.save()              
            return HttpResponseRedirect(reverse('grad:manage_supervisors', kwargs={'grad_slug':grad_slug}))
    else:
        form = SupervisorForm()
        form.set_supervisor_choices(possible_supervisors([grad.program.unit], extras=supervisor_people, null=True))

    context = {
               'form': form,
               'supervisors': supervisors,
               'grad': grad,
               'can_edit': True,
               }
    return render(request, 'grad/manage_supervisors.html', context)
