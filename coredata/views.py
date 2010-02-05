from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from forms import *
from courselib.auth import *
from coredata.models import *
from django.core.urlresolvers import reverse

@requires_role("SYSA")
def importer(request):
    """
    Run the data importer.
    """
    raise NotImplemented
    if request.method == 'POST':
        form = ImportForm(request.POST)
        if form.is_valid():
            return HttpResponse('thanks')
    else:
        form = ImportForm()
    
    return render_to_response('coredata/form.html', {'form': form}, context_instance=RequestContext(request))

@requires_role("SYSA")
def role_list(request):
    """
    Display list of who has what role
    """
    roles = Role.objects.all()
    
    return render_to_response('coredata/roles.html', {'roles': roles}, context_instance=RequestContext(request))

@requires_role("SYSA")
def new_role(request, role=None):
    if request.method == 'POST':
        form = RoleForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse(role_list))
    else:
        form = RoleForm()

    return render_to_response('coredata/new_role.html', {'form': form}, context_instance=RequestContext(request))



