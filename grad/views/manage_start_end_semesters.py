from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
#from coredata.models import Semester
from grad.models import GradStudent
from grad.forms import GradSemesterForm
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect
from django.urls import reverse

@requires_role("GRAD", get_only=["GRPD"])
def manage_start_end_semesters(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    
    if request.method == 'POST':
        form = GradSemesterForm(request.POST)
        if form.is_valid():
            if 'ignore' in form.cleaned_data and form.cleaned_data['ignore']:
                # we have been asked to revert to the default behaviour: clear user-set values
                if 'start_semester' in grad.config:
                    del grad.config['start_semester']
                if 'end_semester' in grad.config:
                    del grad.config['end_semester']
            else:
                # apply the user-set values
                if form.cleaned_data['start_semester']:
                    grad.config['start_semester'] = form.cleaned_data['start_semester'].name
                else:
                    grad.config['start_semester'] = None
    
                if form.cleaned_data['end_semester']:
                    grad.config['end_semester'] = form.cleaned_data['end_semester'].name
                else:
                    grad.config['end_semester'] = None

            grad.save()
            grad.update_status_fields()

            messages.success(request, "Updated start/end semester info for %s." % (grad.person))
            l = LogEntry(userid=request.user.username,
                         description="Updated start/end semester for %s to Start: %s, "
                                     "End: %s" % (grad, grad.config['start_semester'], grad.config['end_semester']),
                         related_object=grad)
            l.save()    
            return HttpResponseRedirect(reverse('grad:view', kwargs={'grad_slug':grad.slug}))
    else:
        form = GradSemesterForm(initial={'start_semester': grad.start_semester, 'end_semester': grad.end_semester})

    context = {
               'form': form,
               'grad': grad,
               }
    return render(request, 'grad/manage_start_end_semesters.html', context)
