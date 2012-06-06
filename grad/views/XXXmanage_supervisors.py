from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, Supervisor
from django.forms.models import modelformset_factory
from grad.forms import SupervisorForm, PotentialSupervisorForm, possible_supervisors
from django import forms
import datetime
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse
from view_all import view_all

@requires_role("GRAD")
def XXXmanage_supervisors(request, grad_slug):
    """
    Like "manage supervisors" but more pornographic. (I can only assume.) 
    """ 
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    supervisors = Supervisor.objects.filter(student=grad, supervisor_type__in=['SEN','COM'], removed=False).select_related('supervisor')
    supervisor_people = [s.supervisor for s in supervisors if s.supervisor]
    # Using filter because get returns an error when there are no matching queries
    pot_supervisor = Supervisor.objects.filter(student=grad, removed=False, supervisor_type='POT') 
    # Initialize potential supervisor to first on of the list of results
    # There should be exactly one match unless there is data error
    extra_form = 0
    if(supervisors.count() == 0):
        extra_form = 1
    if (pot_supervisor.count() == 0):
        pot_supervisor = None
    else:
        pot_supervisor = pot_supervisor[0]
        
    supervisors_formset = modelformset_factory(Supervisor, form=SupervisorForm, extra=extra_form, max_num=4)(queryset=supervisors, prefix="form")
    for f in supervisors_formset:
        f.set_supervisor_choices(possible_supervisors([grad.program.unit], extras=supervisor_people))
        f.fields['position'].widget = forms.HiddenInput()
        if(extra_form == 1):
            f.fields['position'].initial = 1

    if request.method == 'POST':
        potential_supervisors_form = PotentialSupervisorForm(request.POST, instance=pot_supervisor, prefix="pot_sup")
        potential_supervisors_form.set_supervisor_choices(possible_supervisors([grad.program.unit]))
        if potential_supervisors_form.is_valid():
            #change gradstudent's last updated/by info to newest
            grad.updated_at = datetime.datetime.now()
            grad.created_by = request.user.username  
            grad.save()                
            superF = potential_supervisors_form.save(commit=False)
            superF.modified_by = request.user.username
            superF.student = grad #Passing grad student info to model
            superF.position = 0   #Hard coding potential supervisor and passing to model
            superF.supervisor_type = 'POT'
            superF.save()
            messages.success(request, "Updated Potential Supervisor for %s." % (potential_supervisors_form.instance.student))
            l = LogEntry(userid=request.user.username,
                  description="Updated Potential Supervisor for %s." % (potential_supervisors_form.instance.student),
                  related_object=potential_supervisors_form.instance)
            l.save()              
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad_slug}))
    else:
        potential_supervisors_form = PotentialSupervisorForm(instance=pot_supervisor, prefix="pot_sup")
        potential_supervisors_form.set_supervisor_choices(possible_supervisors([grad.program.unit]))

    # check for co-senior supervisor
    second = supervisors.filter(position=2)
    second_co = False
    if second:
        second_co = second[0].supervisor_type=='SEN'

    # set frontend defaults
    page_title = "%s's Supervisor(s) Record" % (grad.person.first_name)
    crumb = "%s, %s" % (grad.person.first_name, grad.person.last_name)
    gp = grad.person.get_fields 
    context = {
               'supervisors_formset': supervisors_formset,
               'second_co': second_co,
               'potential_supervisors_form': potential_supervisors_form,
               'page_title' : page_title,
               'crumb' : crumb,
               'grad' : grad,
               'gp' : gp,
               }
    return render(request, 'grad/manage_supervisors.html', context)
