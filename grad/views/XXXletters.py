from courselib.auth import requires_role
from django.shortcuts import render
from grad.models import Letter

@requires_role("GRAD")
def letters(request):
    letters = Letter.objects.filter(template__unit__in=request.units)

    page_title = 'All Letters'
    crumb = 'Letters'     
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'letters': letters                 
               }
    return render(request, 'grad/letters.html', context)
