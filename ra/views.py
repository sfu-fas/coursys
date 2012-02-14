from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from ra.models import RAAppointment, Project, Account
from ra.forms import RAForm
from grad.forms import possible_supervisors
from coredata.models import Member, Person, Role, Unit
from courselib.auth import requires_role

@requires_role("FUND")
def index(request):
    ras = RAAppointment.objects.all()
    context = {'ras': ras}
    return render(request, 'ra/index.html', context)

@requires_role("FUND")
def new(request):    
    raform = RAForm(request.POST or None)
    raform.fields['hiring_faculty'].choices = possible_supervisors(request.units)
    raform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    if request.method == 'POST':
        if raform.is_valid():
            raform.save()
            return HttpResponseRedirect(reverse(index))
    return render(request, 'ra/new.html', { 'raform': raform })