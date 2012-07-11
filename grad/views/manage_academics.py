from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, GradProgram
from grad.forms import GradAcademicForm
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect, HttpResponse
from django.core.urlresolvers import reverse

@requires_role("GRAD")
def manage_academics(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    program_choices = [(p.id, unicode(p)) for p in GradProgram.objects.filter(unit__in=request.units)]
    
    if request.method == 'POST':
        grad_form = GradAcademicForm(request.POST, instance=grad, prefix="grad")
        grad_form.fields['program'].choices = program_choices
        if grad_form.is_valid():
            gradF = grad_form.save(commit=False)
            gradF.modified_by = request.user.username
            gradF.slug = None
            grad.slug = None
            gradF.save()
            messages.success(request, "Updated Grad Academics for %s." % (grad_form.instance.person))
            l = LogEntry(userid=request.user.username,
                  description="Updated Grad Academics for %s." % (grad_form.instance.person),
                  related_object=grad_form.instance)
            l.save()    
            return HttpResponseRedirect(reverse('grad.views.view', kwargs={'grad_slug':grad.slug}))
    else:
        grad_form = GradAcademicForm(instance=grad, prefix="grad")
        grad_form.fields['program'].choices = program_choices

    # set frontend defaults
    page_title = "%s 's Graduate Academic Record" % (grad.person.first_name)
    crumb = "%s, %s" % (grad.person.first_name, grad.person.last_name)
    gp = grad.person.get_fields 
    context = {
               'grad_form': grad_form,
               'page_title' : page_title,
               'crumb' : crumb,
               'grad' : grad,
               'gp' : gp,
               }
    return render(request, 'grad/manage_academics.html', context)
