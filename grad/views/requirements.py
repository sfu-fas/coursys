from courselib.auth import requires_role
from django.shortcuts import render, get_object_or_404, HttpResponseRedirect, reverse
from django.contrib import messages
from grad.models import GradRequirement
from log.models import LogEntry

@requires_role("GRAD", get_only=["GRPD"])
def requirements(request):
    requirements = GradRequirement.objects.filter(program__unit__in=request.units)

    page_title = 'Graduate Requirements'
    crumb = 'Grad Requirements'     
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'requirements': requirements                 
               }
    return render(request, 'grad/requirements.html', context)


@requires_role("GRAD")
def toggle_requirement(request, requirement_id):
    requirement = get_object_or_404(GradRequirement, pk=requirement_id)
    if request.method == 'POST':
        requirement.hidden = not requirement.hidden
        requirement.save()
        messages.add_message(request,
                             messages.SUCCESS,
                             'Requirement visibility was changed')
        l = LogEntry(userid=request.user.username,
                     description="Changed requirement visibility",
                     related_object=requirement)
        l.save()
    return HttpResponseRedirect(reverse('grad:requirements'))

