from courselib.auth import requires_role
from django.shortcuts import render
from grad.models import GradRequirement

@requires_role("GRAD")
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
