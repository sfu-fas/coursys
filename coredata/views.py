#from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from forms import ImportForm

@login_required
def importer(request):
    """
    Run the data importer.
    """
    if request.method == 'POST': # If the form has been submitted...
        form = ImportForm(request.POST)
        if form.is_valid():
            return HttpResponse('thanks')
    else:
        form = ImportForm() # An unbound form
    
    return render_to_response('coredata/form.html', {'form': form}, context_instance=RequestContext(request))
