from courselib.auth import requires_role
from django.shortcuts import render
from django.contrib import messages
from django.http import HttpResponseRedirect
from grad.forms import new_scholarshipTypeForm
from django.urls import reverse
from .index import index

@requires_role("GRAD")
def manage_scholarshipType(request):
    unit_choices = [(u.id, u.name) for u in request.units]
    if request.method == 'POST':
        scholarshipType_form = new_scholarshipTypeForm(request.POST)
        if scholarshipType_form.is_valid():
            scholarshipType_form.save()
            messages.success(request, "Scholarship Type sucessfully saved.")
            
            return HttpResponseRedirect(reverse('grad:index'))
    else:
        scholarshipType_form = new_scholarshipTypeForm()
        scholarshipType_form.fields['unit'].choices = unit_choices

    page_title = "New Scholarship Type"
   
    context = {'page_title':page_title,
                'new_scholarshipTypeForm': scholarshipType_form
    }
    return render(request, 'grad/manage_scholarshipType.html', context)
