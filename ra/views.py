from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from ra.models import RAAppointment, Project, Account
from ra.forms import RAForm, RASearchForm
from grad.forms import possible_supervisors
from coredata.models import Member, Person, Role, Unit
from courselib.auth import requires_role

@requires_role("FUND")
def appointments(request, student_id=None):
    if student_id:
        student = get_object_or_404(Person, id=student_id)
    else:
        student = None
    
    if request.method == 'POST':
        form = RASearchForm(request.POST)
        if not form.is_valid():
            messages.add_message(request, messages.ERROR, 'Invalid search')
            context = {'form': form}
            return render_to_response('ra/appointments.html', context, context_instance=RequestContext(request))
        search = form.cleaned_data['search']
        return HttpResponseRedirect(reverse('ra.views.student_appointments', kwargs={'userid': search.userid}))
    if student_id:
        form = RASearchForm(instance=student, initial={'student': student.userid})
    else:
        form = RASearchForm()
    context = {'form': form}
    return render_to_response('ra/appointments.html', context, context_instance=RequestContext(request))

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