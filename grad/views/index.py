from courselib.auth import requires_role
from django.shortcuts import render
from grad.forms import QuickSearchForm
from grad.models import SavedSearch

@requires_role("GRAD")
def index(request):
    form = QuickSearchForm()
    savedsearches = SavedSearch.objects.filter(person__userid=(request.user.username))
    other_savedsearches = SavedSearch.objects.exclude(person__userid=(request.user.username))
    context = {'units': request.units, 'form': form, 'savedsearches': savedsearches, 'other_savedsearches':other_savedsearches}
    return render(request, 'grad/index.html', context)
