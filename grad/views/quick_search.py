from grad.models import GradStudent, STATUS_CHOICES, STATUS_ACTIVE, STATUS_APPLICANT, STATUS_INACTIVE, STATUS_CURRENTAPPLICANT
from django.http import HttpResponseRedirect, HttpResponse
from courselib.auth import requires_role, ForbiddenResponse
from courselib.search import get_query
from grad.models import STATUS_CHOICES 
import json, urllib.request, urllib.parse, urllib.error
from django.core.urlresolvers import reverse

def _get_query(term):

    # if "Withdrawn" in search term, search on "WIDR"
    for status, display in STATUS_CHOICES:
        if display in term:
            term = term.replace(display, status)

    return get_query(term, ['person__userid', 'person__emplid', 'person__first_name', 'person__last_name',
                            'person__pref_first_name', 'program__label', 'program__description', 'current_status'],
                     startonly=True)

ACTIVE_STATUS_ORDER = {} # for sorting with active first
for st,_ in STATUS_CHOICES:
    if st in STATUS_ACTIVE:
        ACTIVE_STATUS_ORDER[st] = 0
    elif st in STATUS_CURRENTAPPLICANT:
        ACTIVE_STATUS_ORDER[st] = 1
    elif st in STATUS_INACTIVE:
        ACTIVE_STATUS_ORDER[st] = 2
    elif st in STATUS_APPLICANT:
        ACTIVE_STATUS_ORDER[st] = 3
    else:
        ACTIVE_STATUS_ORDER[st] = 4
ACTIVE_STATUS_ORDER[None] = 5

@requires_role("GRAD", get_only=["GRPD"])
def quick_search(request):
    if 'term' in request.GET:
        term = request.GET['term']
        grads = GradStudent.objects.filter(program__unit__in=request.units) \
                .filter(_get_query(term)) \
                .select_related('person', 'program')[:500] 
                # take more here so the sorting gets more useful students: trim to 50 top later
        
        # sort according to ACTIVE_STATUS_ORDER to get useful students at the top: 
        #   decorate with order, sort, and build jquery response
        grads_sort = [(ACTIVE_STATUS_ORDER[gs.current_status], gs) for gs in grads]
        grads_sort.sort()
        grads_sort = grads_sort[:50]
        
        data = [{'value': str(g.slug), 'label': "%s, %s, %s" % 
                 (g.person.name(), g.program.label, g.get_current_status_display())} 
                 for _,g in grads_sort]
        response = HttpResponse(content_type='application/json')
        json.dump(data, response, indent=1)
        return response
    elif 'search' in request.GET:
        grad_slug = request.GET['search']
        try:
            grad = GradStudent.objects.get(slug=grad_slug, program__unit__in=request.units)
            return HttpResponseRedirect(reverse('grad:view', kwargs={'grad_slug':grad.slug}))
        except GradStudent.DoesNotExist:
            return HttpResponseRedirect(reverse('grad:not_found') + "?search=" + urllib.parse.quote_plus(grad_slug.encode('utf8')))
    else:
        return ForbiddenResponse(request, 'must send term')
