from courselib.auth import requires_role
from coredata.models import Role
from django.shortcuts import render
from grad.forms import QuickSearchForm
from grad.models import SavedSearch

@requires_role("GRAD")
def index(request):
    form = QuickSearchForm()
    savedsearches = SavedSearch.objects.filter(person__userid=(request.user.username))
    other_gradadmin = [r['person_id'] for r in Role.objects.filter(role="GRAD", unit__in=request.units).values('person_id')]
    other_savedsearches = SavedSearch.objects.filter(person__in=other_gradadmin).exclude(person__userid=(request.user.username))
    context = {'units': request.units, 'form': form, 'savedsearches': savedsearches, 'other_savedsearches':other_savedsearches}
    return render(request, 'grad/index.html', context)
