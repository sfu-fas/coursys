from courselib.auth import requires_role
from django.shortcuts import render
from grad.forms import QuickSearchForm 

@requires_role("GRAD")
def index(request):
    form = QuickSearchForm()
    context = {'units': request.units, 'form': form}
    return render(request, 'grad/index.html', context)
