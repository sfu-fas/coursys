from grad.models import GradStudent
from django.http import HttpResponseRedirect, HttpResponse
from courselib.auth import requires_role, ForbiddenResponse
from courselib.search import get_query
import json
from django.core.urlresolvers import reverse
from view_all import view_all

@requires_role("GRAD")
def quick_search(request):
    if 'term' in request.GET:
        term = request.GET['term']
        grads = GradStudent.objects.filter(program__unit__in=request.units) \
                .filter(get_query(term, ['person__userid', 'person__emplid', 'person__first_name', 'person__last_name', 'person__pref_first_name',
                                         'program__label', 'program__description'])) \
                .select_related('person', 'program')[:50]
        data = [{'value': str(g.slug), 'label': "%s, %s" % (g.person.name(), g.program.label)} for g in grads]
        response = HttpResponse(mimetype='application/json')
        json.dump(data, response, indent=1)
        return response
    elif 'search' in request.GET:
        grad_slug = request.GET['search']
        return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad_slug}))
    else:
        return ForbiddenResponse(request, 'must send term')
