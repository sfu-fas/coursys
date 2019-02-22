from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent
from grad.forms import GradAcademicForm, GradFlagValueForm
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect
from django.urls import reverse
import copy

@requires_role("GRAD")
def manage_general(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)

    sin = ''
    if grad.person.sin():
        sin = grad.person.sin()
        
    extra_fields = [field for field, title in grad.tacked_on_fields]

    if request.method == 'POST':
        form = GradAcademicForm(request.POST, instance=grad, initial={'sin':sin} )
        flagforms = [(f, GradFlagValueForm(request.POST, instance=v, prefix='flag-'+str(f.id))) for f, v in grad.flags_and_values()]
        if form.is_valid():
            gradF = form.save(commit=False)

            def optional_fields( field ):
                if form.cleaned_data[field]:
                    gradF.config[field] = form.cleaned_data[field]
                else:
                    if field in gradF.config:
                        del gradF.config[field]
            
            [ optional_fields( field ) for field in extra_fields ] 
            gradF.modified_by = request.user.username
            if form.cleaned_data['sin'] != sin:
                gradF.person.set_sin(form.cleaned_data['sin'])
                gradF.person.save()
            gradF.save()
            for _, fform in flagforms:
                if fform.is_valid():
                    fform.save()

            messages.success(request, "Updated general info for %s." % (form.instance.person))
            l = LogEntry(userid=request.user.username,
                  description="Updated grad general info for %s." % (form.instance.slug),
                  related_object=gradF)
            l.save()    
            return HttpResponseRedirect(reverse('grad:view', kwargs={'grad_slug':grad.slug}))
    else:
        initial = {'sin':sin}
        for x in extra_fields:
            initial[x] = grad.config[x] if x in grad.config else copy.copy(grad.defaults[x])
        form = GradAcademicForm(instance=grad, initial=initial)
        flagforms = [(f, GradFlagValueForm(instance=v, prefix='flag-'+str(f.id))) for f, v in grad.flags_and_values()]

    context = {
               'form': form,
               'grad' : grad,
               'flagforms': flagforms,
               }
    return render(request, 'grad/manage_general.html', context)
