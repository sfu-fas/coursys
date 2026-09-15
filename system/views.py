from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from courselib.auth import requires_global_role
from log.models import LogEntry
from system.forms import SystemVariableForm
from system.models import SystemVariable


@requires_global_role("SYSA")
def list_systemvariables(request):
    variables = SystemVariable.objects.select_related('unit').order_by('key', 'unit__label', 'created_at')
    return render(request, 'system/systemvariables.html', {
        'variables': variables,
    })


@requires_global_role("SYSA")
def new_systemvariable(request):
    if request.method == 'POST':
        form = SystemVariableForm(request.POST)
        if form.is_valid():
            variable = form.save()
            messages.success(request, 'System variable created.')
            l = LogEntry(userid=request.user.username,
                         description=("new system variable: %s (%s)") % (form.instance.key, form.instance.id),
                         related_object=form.instance)
            l.save()
            return HttpResponseRedirect(reverse('system:list_systemvariables'))
    else:
        form = SystemVariableForm()

    return render(request, 'system/new_systemvariable.html', {'form': form, 'is_edit': False})


@requires_global_role("SYSA")
def edit_systemvariable(request, systemvariable_id):
    variable = get_object_or_404(SystemVariable, pk=systemvariable_id)

    if request.method == 'POST':
        form = SystemVariableForm(request.POST, instance=variable)
        if form.is_valid():
            form.save()
            messages.success(request, 'System variable updated.')
            l = LogEntry(userid=request.user.username,
                         description=("updated system variable: %s (%s)") % (form.instance.key, form.instance.id),
                         related_object=form.instance)
            l.save()
            return HttpResponseRedirect(reverse('system:list_systemvariables'))
    else:
        form = SystemVariableForm(instance=variable)

    return render(request, 'system/edit_systemvariable.html', {
        'form': form,
        'variable': variable,
        'title': 'Edit System Variable',
        'is_edit': True,
    })


@requires_global_role("SYSA")
def delete_systemvariable(request, systemvariable_id):
    variable = get_object_or_404(SystemVariable, id=systemvariable_id)
    l = LogEntry(userid=request.user.username,
                 description=("deleted system variable: %s (%s)") % (variable.key, variable.id),
                 related_object=variable)
    l.save()
    variable.delete()
    messages.success(request, 'System variable deleted.')
    return HttpResponseRedirect(reverse('system:list_systemvariables'))
