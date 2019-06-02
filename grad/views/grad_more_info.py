from django.shortcuts import get_object_or_404
from django.http import HttpResponse
import json
from courselib.auth import requires_role
from coredata.queries import more_personal_info, SIMSProblem, GRADFIELDS
from grad.models import GradStudent

@requires_role("GRAD", get_only=["GRPD"])
def grad_more_info(request, grad_slug):
    """
    AJAX request for contact info, etc. (queries SIMS directly)
    """
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    try:
        data = more_personal_info(grad.person.emplid, exclude=GRADFIELDS)
    except SIMSProblem as e:
        data = {'error': str(e)}
    
    response = HttpResponse(content_type='application/json')
    json.dump(data, response, indent=1)
    return response
