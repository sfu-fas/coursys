from courselib.auth import requires_role
from grad.models import GradStudent
from django.http import HttpResponse
from grad.forms import SearchForm
import datetime, json

@requires_role("GRAD")
def search_results(request):
    """
    DataTables data for grad result display

    See: http://www.datatables.net/usage/server-side
    """
    if len(request.GET) == 0:
        form = SearchForm()
    else:
        form = SearchForm(request.GET)
    rows = []
    data = {}
    if form.is_valid():
        try:
            start = int(request.GET['iDisplayStart'])
            count = int(request.GET['iDisplayLength'])
        except (KeyError, ValueError):
            start = 0
            count = 200
        results = GradStudent.objects.filter(program__unit__in=request.units).select_related('person')
        total = results.count()
        results = list(results)
        results = results + results + results + results + results + results
        grads = results[start:start + count]
        for g in grads:
            rows.append([g.person.emplid])
        
        print rows
        data = {
                'iTotalRecords': total * 6,
                'aaData': rows,
                }
    if 'sEcho' in request.GET:
        data['sEcho'] = request.GET['sEcho']
    resp = HttpResponse(mimetype="application/json")
    json.dump(data, resp, indent=1)
    return resp
