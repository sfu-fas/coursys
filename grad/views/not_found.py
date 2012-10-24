from grad.models import GradStudent
from courselib.auth import requires_role
from django.shortcuts import render
from quick_search import _get_query
from courselib.auth import ForbiddenResponse

@requires_role("GRAD")
def not_found(request):
    """
    View to handle the enter-search/press-enter behaviour in the autocomplete box
    """
    if 'search' not in request.GET:
        return ForbiddenResponse(request, 'must give search in query')
    search = request.GET['search']
    grads = GradStudent.objects.filter(program__unit__in=request.units) \
                .filter(_get_query(search)) \
                .select_related('person', 'program')[:500]
    context = {'grads': grads}
    return render(request, 'grad/not_found.html', context)