from courselib.auth import requires_role, ForbiddenResponse
from django.shortcuts import get_object_or_404
from grad.models import GradStudent
from django.http import HttpResponse
from coredata.queries import more_personal_info, SIMSProblem
import json

@requires_role("GRAD", get_only=["GRPD"])
def get_addresses(request):
    if 'id' not in request.GET:
        return ForbiddenResponse(request, 'must send id')
    sid = request.GET['id']
    grad = get_object_or_404(GradStudent, id=sid, program__unit__in=request.units)
    emplid = grad.person.emplid
    
    try:
        data = more_personal_info(emplid, needed=['addresses'])
        if data:
            data['full_name'] = "%s\n" % grad.person.name()
    except SIMSProblem as e:
        data = {'error': str(e)}
        
    resp = HttpResponse(content_type="application/json")
    json.dump(data, resp, indent=1)
    return resp
