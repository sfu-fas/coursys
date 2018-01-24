from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, GradStatus, STATUS_CHOICES, STATUS_OBSOLETE
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect
from grad.forms import GradStatusForm
import datetime
from coredata.models import Semester
from django.urls import reverse

@requires_role("GRAD")
def manage_status(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    statuses = GradStatus.objects.filter(student=grad)
    # remove obsolete statuses from the list (but not the model, so legacy data displays properly)
    status_choices = [(k,v) for k,v in STATUS_CHOICES if k not in STATUS_OBSOLETE]

    if request.method == 'POST':
        form = GradStatusForm(request.POST)
        form.fields['status'].choices = status_choices
        if form.is_valid():
            # Save new status
            status = form.save(commit=False)
            status.student = grad
            status.save()
            
            #change gradstudent's last updated/by info to newest
            grad.updated_at = datetime.datetime.now()
            grad.created_by = request.user.username
            grad.save()
            
            messages.success(request, "Updated Status History for %s." % (grad.person))
            l = LogEntry(userid=request.user.username,
                    description="Updated Status History for %s." % (grad.person),
                    related_object=status)
            l.save()                       
            return HttpResponseRedirect(reverse('grad:manage_status', kwargs={'grad_slug':grad_slug}))
    else:
        form = GradStatusForm(initial={'start': Semester.current(), 'start_date': datetime.datetime.today()})
        form.fields['status'].choices = status_choices

    context = {
               'form' : form,
               'statuses' : statuses,
               'grad' : grad,
               'can_edit': True,
               }
    return render(request, 'grad/manage_status.html', context)
