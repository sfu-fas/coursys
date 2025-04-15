from courselib.auth import requires_role
from django.shortcuts import render
from grad.models import GradStudent, Supervisor, STATUS_ACTIVE
from grad.forms import BulkSupervisorForm, possible_supervisors
from log.models import LogEntry
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.forms import formset_factory

def _get_grads_missing_supervisors(units):
    grads = GradStudent.objects.filter(program__requires_supervisor=True, current_status__in=STATUS_ACTIVE, program__unit__in=units).order_by("start_semester", "person__sortname", "program__unit", "program__label")
    # list of students with supervisors
    ids_with_supervisors = [grad.id for grad in grads if grad.has_supervisor(include_potential=True)]
    grads = grads.exclude(id__in=ids_with_supervisors)
    return grads

@requires_role("GRAD", get_only=["GRPD"])
def add_supervisors(request):
    grads = _get_grads_missing_supervisors(request.units)
    rows = []
    max_forms_per_grad = 5
    SupervisorFormSet = formset_factory(BulkSupervisorForm, max_num=max_forms_per_grad, absolute_max=max_forms_per_grad)
    for grad in grads:
        formset = SupervisorFormSet(data=request.POST or None, prefix=grad.slug)
        supervisors = Supervisor.objects.filter(student=grad).select_related('supervisor')
        supervisor_people = [s.supervisor for s in supervisors if s.supervisor]
        for form in formset:
            form.set_supervisor_choices(possible_supervisors([grad.program.unit], extras=supervisor_people, null=True))
        rows.append({'grad': grad, 'formset': formset})
    if request.method == 'POST':
        admin = request.user.username
        updated_rows = []
        all_formsets_valid = True
        for i in range (len(grads)):
            formset = rows[i]['formset']
            if not formset.is_valid():
                all_formsets_valid = False
        if all_formsets_valid:
            for i in range (len(grads)):
                grad = grads[i]
                formset = rows[i]['formset']
                for form in formset:
                    if form.is_valid() and not form.cleaned_data['empty']:
                        s = form.save(commit=False)
                        s.modified_by = admin
                        s.student = grad
                        s.save()
                        #LOG EVENT
                        l = LogEntry(userid=request.user.username,
                        description="Bulk added committee member %s for %s." % (s, grad.person.userid),
                        related_object=grad)
                        l.save()  
                        updated_rows.append({'grad': grad, 'formset': formset})
            num_updated_rows = len(updated_rows)
            if num_updated_rows > 0:
                messages.add_message(request, messages.SUCCESS, "Added %s Committee Members" % (num_updated_rows ))
                for row in updated_rows:
                    if row in rows:
                        rows.remove(row)
            return HttpResponseRedirect(reverse('grad:add_supervisors'))
    return render(request, 'grad/add_supervisors.html', {'grads': grads, 'rows': rows, 'max_forms_per_grad': max_forms_per_grad})

@requires_role(["GRAD", "GRPD"])
def committee_info(request):
    context = {}
    return render(request, "grad/committee_info.html", context)