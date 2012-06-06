from courselib.auth import requires_role
from django.shortcuts import render
from grad.models import LetterTemplate

@requires_role("GRAD")
def letter_templates(request):
    templates = LetterTemplate.objects.filter(unit__in=request.units)

    page_title = 'Letter Templates'
    crumb = 'Letter Templates'     
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'templates': templates                 
               }
    return render(request, 'grad/letter_templates.html', context)
