from courselib.auth import requires_role
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.http import HttpResponseRedirect
from grad.forms import ScholarshipTypeForm
from grad.models import ScholarshipType
from django.urls import reverse
from log.models import LogEntry


@requires_role("GRAD")
def new_scholarshiptype(request):
    unit_choices = [(u.id, u.name) for u in request.units]
    if request.method == 'POST':
        form = ScholarshipTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Scholarship Type sucessfully saved.")
            
            return HttpResponseRedirect(reverse('grad:manage_scholarshiptypes'))
    else:
        form = ScholarshipTypeForm()
        form.fields['unit'].choices = unit_choices

    page_title = "New Scholarship Type"
   
    context = {'page_title':page_title, 'form': form}
    return render(request, 'grad/new_scholarshiptype.html', context)


@requires_role("GRAD")
def manage_scholarshiptypes(request):
    sts = ScholarshipType.objects.filter(unit__in=request.units)
    return render(request, 'grad/manage_scholarshiptypes.html', {'sts': sts})


@requires_role("GRAD")
def edit_scholarshiptype(request, st_id):
    st = get_object_or_404(ScholarshipType, pk=st_id, unit__in=request.units)
    unit_choices = [(u.id, u.name) for u in request.units]
    if request.method == 'POST':
        form = ScholarshipTypeForm(request.POST, instance=st)
        if form.is_valid():
            form.save()
            messages.success(request, "Scholarship Type sucessfully saved.")

            return HttpResponseRedirect(reverse('grad:manage_scholarshiptypes'))
    else:
        form = ScholarshipTypeForm(instance=st)
        form.fields['unit'].choices = unit_choices

    page_title = "New Scholarship Type"

    context = {'page_title': page_title, 'form': form}
    return render(request, 'grad/new_scholarshiptype.html', context)


@requires_role("GRAD")
def toggle_scholarshiptype(request, st_id):
    st = get_object_or_404(ScholarshipType, pk=st_id, unit__in=request.units)
    if request.method == 'POST':
        st.hidden = not st.hidden
        st.save()
        messages.add_message(request,
                             messages.SUCCESS,
                             'Scholarship type visibility was changed')
        l = LogEntry(userid=request.user.username,
                     description="Changed scholarship type visibility",
                     related_object=st)
        l.save()
    return HttpResponseRedirect(reverse('grad:manage_scholarshiptypes'))
