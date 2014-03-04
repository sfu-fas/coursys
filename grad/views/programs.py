from courselib.auth import requires_role
from django.shortcuts import render
from grad.models import GradProgram

@requires_role("GRAD", get_only=["GRPD"])
def programs(request):
    programs = GradProgram.objects.filter(unit__in=request.units)
    
    # set frontend defaults
    page_title = 'Graduate Programs'
    crumb = 'Grad Programs' 
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'programs': programs               
               }
    return render(request, 'grad/programs.html', context)
