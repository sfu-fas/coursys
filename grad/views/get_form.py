from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from courselib.auth import NotFoundResponse, requires_role
from grad.models import GradStudent
from dashboard.letters import card_req_forms, fasnet_forms

@requires_role("GRAD")
def get_form(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    
    if 'type' in request.GET and request.GET['type'] == 'cardreq':
        response = HttpResponse(mimetype='application/pdf')
        response['Content-Disposition'] = 'inline; filename=card_access.pdf'
        card_req_forms([grad], response)
    elif 'type' in request.GET and request.GET['type'] == 'fasnet':
        response = HttpResponse(mimetype='application/pdf')
        response['Content-Disposition'] = 'inline; filename=fasnet_access.pdf'
        fasnet_forms([grad], response)
    else:
        response = NotFoundResponse(request)
    
    return response
