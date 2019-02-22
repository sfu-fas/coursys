from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, Supervisor
from grad.forms import GradDefenceForm, possible_supervisors
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db import transaction

@requires_role("GRAD")
def manage_defence(request, grad_slug):
    """
    Page for managing all defence-related stuff.
    
    Slightly complicated since this info cuts across several models.
    """
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    supervisors = Supervisor.objects.filter(student=grad).select_related('supervisor')
    supervisor_people = [s.supervisor for s in supervisors if s.supervisor]
    supervisor_choices = possible_supervisors(units=request.units, extras=supervisor_people, null=True)
        
    if request.method == 'POST':
        form = GradDefenceForm(request.POST)
        form.set_supervisor_choices(supervisor_choices)
        if form.is_valid():
            with transaction.atomic():
                grad.config['thesis_type'] = form.cleaned_data['thesis_type']
                grad.config['work_title'] = form.cleaned_data['work_title']
                grad.config['exam_date'] = form.cleaned_data['exam_date']
                grad.config['thesis_outcome'] = form.cleaned_data['thesis_outcome']
                grad.config['thesis_location'] = form.cleaned_data['thesis_location']
                grad.save()
                
                if form.cleaned_data['internal']:
                    p = form.cleaned_data['internal']
                    # remove any old ones
                    remove_sup = Supervisor.objects.filter(student=grad, removed=False, supervisor_type='SFU').exclude(supervisor=p)
                    for sup in remove_sup:
                        sup.removed = True
                        sup.save()
                    
                    existing_sup = Supervisor.objects.filter(student=grad, removed=False, supervisor_type='SFU', supervisor=p)
                    if not existing_sup:
                        # doesn't exist: create
                        sup = Supervisor(student=grad, supervisor_type='SFU', supervisor=p)
                        sup.save()
                    # else: already there, so nothing to change
                
                if form.cleaned_data['chair']:
                    p = form.cleaned_data['chair']
                    # remove any old ones
                    remove_sup = Supervisor.objects.filter(student=grad, removed=False, supervisor_type='CHA').exclude(supervisor=p)
                    for sup in remove_sup:
                        sup.removed = True
                        sup.save()
                    
                    existing_sup = Supervisor.objects.filter(student=grad, removed=False, supervisor_type='CHA', supervisor=p)
                    if not existing_sup:
                        # doesn't exist: create
                        sup = Supervisor(student=grad, supervisor_type='CHA', supervisor=p)
                        sup.save()
                    # else: already there, so nothing to change

                if form.cleaned_data['external']:
                    name = form.cleaned_data['external']
                    # remove any old ones
                    remove_sup = Supervisor.objects.filter(student=grad, removed=False, supervisor_type='EXT').exclude(external=name)
                    for sup in remove_sup:
                        sup.removed = True
                        sup.save()
                    
                    # creqate/update
                    existing_sup = Supervisor.objects.filter(student=grad, removed=False, supervisor_type='EXT', external=name)
                    if existing_sup:
                        sup = existing_sup[0]
                    else:
                        sup = Supervisor(student=grad, supervisor_type='EXT', external=name)
                    
                    sup.config['email'] = form.cleaned_data['external_email']
                    sup.config['contact'] = form.cleaned_data['external_contact']
                    sup.config['attend'] = form.cleaned_data['external_attend']
                    sup.save()

            messages.success(request, "Updated defence info for %s." % (grad.person))
            l = LogEntry(userid=request.user.username,
                  description="Updated grad defence info for %s." % (grad),
                  related_object=grad)
            l.save()    
            return HttpResponseRedirect(reverse('grad:view', kwargs={'grad_slug':grad.slug}))
    else:
        initial = {}
        if 'thesis_type' in grad.config:
            initial['thesis_type'] = grad.config['thesis_type']
        if 'work_title' in grad.config:
            initial['work_title'] = grad.config['work_title']
        if 'exam_date' in grad.config:
            initial['exam_date'] = grad.config['exam_date']
        if 'thesis_outcome' in grad.config:
            initial['thesis_outcome'] = grad.config['thesis_outcome']
        if 'thesis_location' in grad.config:
            initial['thesis_location'] = grad.config['thesis_location']
        internals = Supervisor.objects.filter(student=grad, removed=False, supervisor_type='SFU')
        if internals:
            initial['internal'] = internals[0].supervisor_id
        chairs = Supervisor.objects.filter(student=grad, removed=False, supervisor_type='CHA')
        if chairs:
            initial['chair'] = chairs[0].supervisor_id
        externals = Supervisor.objects.filter(student=grad, removed=False, supervisor_type='EXT')
        if externals:
            ext = externals[0]
            initial['external'] = ext.external
            initial['external_email'] = ext.config.get('email', '')
            initial['external_contact'] = ext.config.get('contact', '')
            initial['external_attend'] = ext.config.get('attend', '')

        form = GradDefenceForm(initial=initial)
        form.set_supervisor_choices(supervisor_choices)        

    context = {
               'form': form,
               'grad': grad,
               }
    return render(request, 'grad/manage_defence.html', context)
