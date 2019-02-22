from courselib.auth import requires_role
from django.shortcuts import render
from django.contrib import messages
from log.models import LogEntry
from django.http import HttpResponseRedirect, HttpResponse
from grad.forms import UploadApplicantsForm
from django.urls import reverse
from coredata.models import Person, Semester
from django.conf import settings

@requires_role("GRAD", get_only=["GRPD"])
def XXX_import_applic(request):
    unit_choices = [(u.id, u.name) for u in request.units]
    semester_choices = [(s.id, s.label()) for s in Semester.objects.filter()]
    if request.method == 'POST':
        form = UploadApplicantsForm(data=request.POST, files=request.FILES)
        form.fields['unit'].choices = unit_choices
        form.fields['semester'].choices = semester_choices
        if form.is_valid():
            data = form.cleaned_data['csvfile'].read()
            unit_id = form.cleaned_data['unit']
            semester_id = form.cleaned_data['semester']
            user = Person.objects.get(userid=request.user.username)
            if settings.USE_CELERY:
                from grad.tasks import process_pcs_task
                process_pcs_task.delay(data, unit_id, semester_id, user)
                messages.success(request, "Importing applicant data. You will receive an email with the results in a few minutes.")
            else:
                from grad.forms import process_pcs_export
                res = process_pcs_export(data, unit_id, semester_id, user)
                messages.success(request, "Imported applicant data.")
                return HttpResponse('<pre>'+res+'</pre>')       

            return HttpResponseRedirect(reverse('grad:index'))
    else:
        next_sem = Semester.next_starting()
        form = UploadApplicantsForm(initial={'semester': next_sem.id})
        form.fields['unit'].choices = unit_choices
        form.fields['semester'].choices = semester_choices

    context = {
               'form': form,
               }
    return render(request, 'grad/import_applic.html', context)
