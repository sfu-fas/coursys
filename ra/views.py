from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib import messages
from ra.models import RAAppointment, Project, Account
from ra.forms import RAForm, RASearchForm, AccountForm, ProjectForm
from grad.forms import possible_supervisors
from coredata.models import Member, Person, Role, Unit
from courselib.auth import requires_role
from django.template import RequestContext

@requires_role("FUND")
def search(request, student_id=None):
    if student_id:
        student = get_object_or_404(Person, id=student_id)
    else:
        student = None
    
    if request.method == 'POST':
        form = RASearchForm(request.POST)
        if not form.is_valid():
            messages.add_message(request, messages.ERROR, 'Invalid search')
            context = {'form': form}
            return render_to_response('ra/search.html', context, context_instance=RequestContext(request))
        search = form.cleaned_data['search']
        return HttpResponseRedirect(reverse('ra.views.student_appointments', kwargs={'userid': search.userid}))
    if student_id:
        form = RASearchForm(instance=student, initial={'student': student.userid})
    else:
        form = RASearchForm()
    context = {'form': form}
    return render_to_response('ra/search.html', context, context_instance=RequestContext(request))

@requires_role("FUND")
def student_appointments(request, userid):
    depts = Role.objects.filter(person__userid=request.user.username, role='FUND').values('unit_id')
    appointments = RAAppointment.objects.filter(person__userid=userid, unit__id__in=depts).order_by("-created_at")
    student = Person.objects.get(userid=userid)
    return render(request, 'ra/student_appointments.html', {'appointments': appointments, 'student': student}, context_instance=RequestContext(request))

@requires_role("FUND")
def new(request):    
    raform = RAForm(request.POST or None)
    raform.fields['hiring_faculty'].choices = possible_supervisors(request.units)
    raform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    raform.fields['project'].choices = [(p.id, unicode(p.project_number)) for p in Project.objects.filter(unit__in=request.units)]
    raform.fields['account'].choices = [(a.id, u'%s (%s)' % (a.account_number, a.title)) for a in Account.objects.filter(unit__in=request.units)]
    if request.method == 'POST':
        if raform.is_valid():
            raform.save()
            return HttpResponseRedirect(reverse(search))
    return render(request, 'ra/new.html', { 'raform': raform })

@requires_role("FUND")
def edit(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug)    
    raform = RAForm(request.POST or None)
    raform.fields['hiring_faculty'].choices = possible_supervisors(request.units)
    raform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    raform.fields['project'].choices = [(p.id, unicode(p.project_number)) for p in Project.objects.filter(unit__in=request.units)]
    raform.fields['account'].choices = [(a.id, u'%s (%s)' % (a.account_number, a.title)) for a in Account.objects.filter(unit__in=request.units)]
    if request.method == 'POST':
        if raform.is_valid():
            appointment = raform.save()
            appointment.save()
            return HttpResponseRedirect(reverse(view, args=(ra_slug)))
    else:
        raform = RAForm(instance=appointment)
    return render(request, 'ra/edit.html', { 'raform': raform })

@requires_role("FUND")
def view(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug)
    student = Person.objects.get(userid=appointment.person.userid)
    return render(request, 'ra/view.html', {'appointment': appointment, 'student': student}, context_instance=RequestContext(request))

@requires_role("FUND")
def new_account(request):
    accountform = AccountForm(request.POST or None)
    accountform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    if request.method == 'POST':
        if accountform.is_valid():
            accountform.save()
            return HttpResponseRedirect(reverse('ra.views.accounts_index'))
    return render(request, 'ra/new_account.html', {'accountform': accountform})

@requires_role("FUND")
def accounts_index(request):
    depts = Role.objects.filter(person__userid=request.user.username, role='FUND').values('unit_id')
    accounts = Account.objects.filter(unit__id__in=depts).order_by("account_number")
    return render(request, 'ra/accounts_index.html', {'accounts': accounts}, context_instance=RequestContext(request))

@requires_role("FUND")
def delete_account(request, account_slug):
    account = get_object_or_404(Account, slug=account_slug)
    messages.success(request, 'Deleted account ' + str(account.account_number))
    account.delete()
    return HttpResponseRedirect(reverse(accounts_index))

@requires_role("FUND")
def edit_account(request, account_slug):
    account = get_object_or_404(Account, slug=account_slug)
    if request.method == 'POST':
        accountform = AccountForm(request.POST, instance=account)
        if accountform.is_valid():
            accountform.save()
            return HttpResponseRedirect(reverse(accounts_index))
    else:
        accountform = AccountForm(instance=account)
        accountform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    return render(request, 'ra/edit_account.html', {'accountform': accountform, 'account': account}, context_instance=RequestContext(request))

@requires_role("FUND")
def new_project(request):
    projectform = ProjectForm(request.POST or None)
    projectform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    if request.method == 'POST':
        if projectform.is_valid():
            projectform.save()
            return HttpResponseRedirect(reverse('ra.views.projects_index'))
    return render(request, 'ra/new_project.html', {'projectform': projectform})

@requires_role("FUND")
def projects_index(request):
    depts = Role.objects.filter(person__userid=request.user.username, role='FUND').values('unit_id')
    projects = Project.objects.filter(unit__id__in=depts).order_by("project_number")
    return render(request, 'ra/projects_index.html', {'projects': projects}, context_instance=RequestContext(request))

@requires_role("FUND")
def delete_project(request, project_slug):
    project = get_object_or_404(Project, slug=project_slug)
    messages.success(request, 'Deleted project ' + str(project.project_number))
    project.delete()
    return HttpResponseRedirect(reverse(projects_index))

@requires_role("FUND")
def edit_project(request, project_slug):
    project = get_object_or_404(Project, slug=project_slug)
    if request.method == 'POST':
        projectform = ProjectForm(request.POST, instance=project)
        if projectform.is_valid():
            projectform.save()
            return HttpResponseRedirect(reverse(projects_index))
    else:
        projectform = ProjectForm(instance=project)
        projectform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    return render(request, 'ra/edit_project.html', {'projectform': projectform, 'project': project}, context_instance=RequestContext(request))