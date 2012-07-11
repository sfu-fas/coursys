from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, get_list_or_404, render
from grad.models import GradStudent, GradStatus
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect, HttpResponse
from grad.forms import GradStatusForm
import datetime
from coredata.models import Semester
from django.core.urlresolvers import reverse

@requires_role("GRAD")
def manage_status(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    status_history = get_list_or_404(GradStatus, student=grad.id, hidden=False)

    if request.method == 'POST':
        new_status_form = GradStatusForm(request.POST)
        if new_status_form.is_valid():
            # Save new status
            new_actual_status = new_status_form.save(commit=False)
            new_actual_status.student = grad
            new_actual_status.save()
            
            #change gradstudent's last updated/by info to newest
            grad.updated_at = datetime.datetime.now()
            grad.created_by = request.user.username
            grad.save()
            
            messages.success(request, "Updated Status History for %s." % (grad.person))
            l = LogEntry(userid=request.user.username,
                    description="Updated Status History for %s." % (grad.person),
                    related_object=new_status_form.instance)
            l.save()                       
            return HttpResponseRedirect(reverse('grad.views.view', kwargs={'grad_slug':grad_slug}))
    else:
        new_status_form = GradStatusForm(initial={'start': Semester.current(), 'start_date': None})

    # set frontend defaults
    gp = grad.person.get_fields
    context = {
               'new_status' : new_status_form,
               'status_history' : status_history,
               'grad' : grad,
               'gp' : gp
               }
    return render(request, 'grad/manage_status.html', context)
