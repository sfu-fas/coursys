from courselib.auth import requires_role
from grad.models import GradStudent, Supervisor
from django.shortcuts import get_object_or_404, render
from django.forms.models import modelformset_factory
import datetime
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from view_all import view_all
from manage_supervisors import manage_supervisors


@requires_role("GRAD")
def XXX_update_supervisors(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    supervisors = Supervisor.objects.filter(student=grad, supervisor_type__in=['SEN','COM'], removed=False).select_related('supervisor')
    supervisor_people = [s.supervisor for s in supervisors if s.supervisor]
    if request.method == 'POST':
        supervisors_formset = modelformset_factory(Supervisor, form=SupervisorForm, formset=BaseSupervisorsFormSet)(request.POST, prefix="form")
        for f in supervisors_formset:
            f.set_supervisor_choices(possible_supervisors([grad.program.unit], extras=supervisor_people))
            f.fields['position'].widget = forms.HiddenInput()
        
        if supervisors_formset.is_valid():
            second_co = 'second-co' in request.POST # is second supervisor is co-senior checked?
            #change gradstudent's last updated info to newest
            grad.updated_at = datetime.datetime.now()
            grad.created_by = request.user.username  
            grad.save()
            for s in supervisors_formset:
                # infer supervisor_type from other fields we have
                s.instance.supervisor_type = 'SEN' if s.cleaned_data['position'] == 1 else 'COM'
                if second_co and 'position' in s.cleaned_data and s.cleaned_data['position'] == 2:
                    s.instance.supervisor_type = 'SEN'

                s.instance.student = grad
            
            supervisors_formset.save()
                    
            messages.success(request, "Updated Supervisor(s) for %s." % (grad))
            l = LogEntry(userid=request.user.username,
                  description="Updated Supervisor(s) for %s." % (grad),
                  related_object=grad)
            l.save()
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad_slug}))
        else:
            page_title = "%s's Supervisor(s) Record" % (grad.person.first_name)
            crumb = "%s, %s" % (grad.person.first_name, grad.person.last_name)
            gp = grad.person.get_fields 
            context = {
               'supervisors_formset': supervisors_formset,
               #'potential_supervisors_form': potential_supervisors_form,
               'page_title' : page_title,
               'crumb' : crumb,
               'grad' : grad,
               'gp' : gp,
               }
            return render(request, 'grad/manage_supervisors.html', context)
            #return HttpResponseRedirect(reverse(manage_supervisors, kwargs={'grad_slug':grad_slug}))

    else:
        return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug': grad_slug}))
