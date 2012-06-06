from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib import messages
from ra.models import RAAppointment, Project, Account
from ra.forms import RAForm, RASearchForm, AccountForm, ProjectForm
from grad.forms import possible_supervisors
from coredata.models import Person, Role, Semester
from courselib.auth import requires_role, ForbiddenResponse
from courselib.search import find_userid_or_emplid
from django.template import RequestContext
from grad.models import GradStudent, Scholarship
from dashboard.letters import ra_form, OfficialLetter, LetterContents
from django import forms

import json

#This is the search function that that returns a list of RA Appointments related to the query.
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
        # deal with people without active computing accounts
        if search.userid:
            userid = search.userid
        else:
            userid = search.emplid
        return HttpResponseRedirect(reverse('ra.views.student_appointments', kwargs={'userid': userid}))
    if student_id:
        form = RASearchForm(instance=student, initial={'student': student.userid})
    else:
        form = RASearchForm()
    context = {'form': form}
    return render_to_response('ra/search.html', context, context_instance=RequestContext(request))




#This is an index of all RA Appointments belonging to a given person.
@requires_role("FUND")
def student_appointments(request, userid):
    #depts = Role.objects.filter(person__userid=request.user.username, role='FUND').values('unit_id')
    student = get_object_or_404(Person, find_userid_or_emplid(userid))
    appointments = RAAppointment.objects.filter(person=student, unit__in=request.units).order_by("-created_at")
    return render(request, 'ra/student_appointments.html', {'appointments': appointments, 'student': student}, context_instance=RequestContext(request))

def _appointment_defaults(units, emplid=None):
    hiring_faculty_choices = possible_supervisors(units)
    unit_choices = [(u.id, u.name) for u in units]
    project_choices = [(p.id, unicode(p)) for p in Project.objects.filter(unit__in=units)]
    account_choices = [(a.id, unicode(a)) for a in Account.objects.filter(unit__in=units)]
    scholarship_choices = [("", u'\u2014')]
    if emplid:
        for s in Scholarship.objects.filter(student__person__emplid=emplid):
            scholarship_choices.append((s.pk, s.scholarship_type.unit.label + ": " + s.scholarship_type.name + " (" + s.start_semester.name + " to " + s.end_semester.name + ")"))

    return (scholarship_choices, hiring_faculty_choices, unit_choices, project_choices, account_choices)
    

#New RA Appointment
@requires_role("FUND")
def new(request):
    scholarship_choices, hiring_faculty_choices, unit_choices, project_choices, account_choices =_appointment_defaults(request.units)
    if request.method == 'POST':
        data = request.POST.copy()
        if data['pay_frequency'] == 'L':
            # force values into the non-submitted (and don't-care) fields for lump sum pay
            try:
                pay = float(data['lump_sum_pay'])
            except ValueError:
                pay = 1
            data['biweekly_pay'] = data.get('biweekly_pay', pay)
            data['hourly_pay'] = data.get('hourly_pay', pay)
            data['hours'] = 1
            data['pay_periods'] = 1

        raform = RAForm(data)
        raform.fields['hiring_faculty'].choices = hiring_faculty_choices
        raform.fields['unit'].choices = unit_choices
        raform.fields['project'].choices = project_choices
        raform.fields['account'].choices = account_choices

        if raform.is_valid():
            userid = raform.cleaned_data['person'].userid
            appointment = raform.save()
            messages.success(request, 'Created RA Appointment for ' + appointment.person.name())
            return HttpResponseRedirect(reverse(student_appointments, kwargs=({'userid': userid})))
    else:
        semester = Semester.next_starting() 
        raform = RAForm(initial={'start_date': semester.start, 'end_date': semester.end, 'hours': 70 })
        raform.fields['scholarship'].choices = scholarship_choices
        raform.fields['hiring_faculty'].choices = hiring_faculty_choices
        raform.fields['unit'].choices = unit_choices
        raform.fields['project'].choices = project_choices
        raform.fields['account'].choices = account_choices
    return render(request, 'ra/new.html', { 'raform': raform })

#New RA Appointment with student pre-filled.
@requires_role("FUND")
def new_student(request, userid):
    person = get_object_or_404(Person, emplid=userid)
    semester = Semester.first_relevant() 
    student = get_object_or_404(Person, find_userid_or_emplid(userid))
    initial = {'person': student.emplid, 'start_date': semester.start, 'end_date': semester.end, 'hours': 70 }
    scholarship_choices, hiring_faculty_choices, unit_choices, project_choices, account_choices =_appointment_defaults(request.units, emplid=student.emplid)
    try:
        gradstudent = GradStudent.objects.get(person=student)
        initial['sin'] = gradstudent.sin()
    except GradStudent.DoesNotExist:
        pass    
    raform = RAForm(initial=initial)
    raform.fields['person'] = forms.CharField(widget=forms.HiddenInput())
    raform.fields['scholarship'].choices = scholarship_choices
    raform.fields['hiring_faculty'].choices = hiring_faculty_choices
    raform.fields['unit'].choices = unit_choices
    raform.fields['project'].choices = project_choices
    raform.fields['account'].choices = account_choices
    return render(request, 'ra/new.html', { 'raform': raform, 'person': person })

#Edit RA Appointment
@requires_role("FUND")
def edit(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug)    
    scholarship_choices, hiring_faculty_choices, unit_choices, project_choices, account_choices = _appointment_defaults(request.units, emplid=appointment.person.emplid)
    if request.method == 'POST':
        data = request.POST.copy()
        if data['pay_frequency'] == 'L':
            # force values into the non-submitted (and don't-care) fields for lump sum pay
            try:
                pay = float(data['lump_sum_pay'])
            except ValueError:
                pay = 1
            data['biweekly_pay'] = data.get('biweekly_pay', pay)
            data['hourly_pay'] = data.get('hourly_pay', pay)
            data['hours'] = 1
            data['pay_periods'] = 1
        
        raform = RAForm(data, instance=appointment)
        if raform.is_valid():
            userid = raform.cleaned_data['person'].userid
            raform.save()
            messages.success(request, 'Updated RA Appointment for ' + appointment.person.first_name + " " + appointment.person.last_name)
            return HttpResponseRedirect(reverse(student_appointments, kwargs=({'userid': userid})))
    else:
        #The initial value needs to be the person's emplid in the form. Django defaults to the pk, which is not human readable.
        raform = RAForm(instance=appointment, initial={'person': appointment.person.emplid})
        #As in the new method, choices are restricted to relevant options.
        raform.fields['person'] = forms.CharField(widget=forms.HiddenInput())
        raform.fields['hiring_faculty'].choices = hiring_faculty_choices
        raform.fields['scholarship'].choices = scholarship_choices
        raform.fields['unit'].choices = unit_choices
        raform.fields['project'].choices = project_choices
        raform.fields['account'].choices = account_choices
    return render(request, 'ra/edit.html', { 'raform': raform, 'appointment': appointment })

#Quick Reappoint, The difference between this and edit is that the reappointment box is automatically checked, and date information is filled out as if a new appointment is being created.
#Since all reappointments will be new appointments, no post method is present, rather the new appointment template is rendered with the existing data which will call the new method above when posting.
@requires_role("FUND")
def reappoint(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug)    
    semester = Semester.first_relevant()
    raform = RAForm(instance=appointment, initial={'person': appointment.person.emplid, 'reappointment': True, 'start_date': semester.start, 'end_date': semester.end, 'hours': 70 })
    raform.fields['hiring_faculty'].choices = possible_supervisors(request.units)
    scholarship_choices = [("", "---------")]
    for s in Scholarship.objects.filter(student__person__emplid = appointment.person.emplid):
            scholarship_choices.append((s.pk, s.scholarship_type.unit.label + ": " + s.scholarship_type.name + " (" + s.start_semester.name + " to " + s.end_semester.name + ")"))
    raform.fields['scholarship'].choices = scholarship_choices
    raform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    raform.fields['project'].choices = [(p.id, unicode(p.project_number)) for p in Project.objects.filter(unit__in=request.units)]
    raform.fields['account'].choices = [(a.id, u'%s (%s)' % (a.account_number, a.title)) for a in Account.objects.filter(unit__in=request.units)]
    return render(request, 'ra/new.html', { 'raform': raform, 'appointment': appointment })

#View RA Appointment
@requires_role("FUND")
def view(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug)
    student = appointment.person
    return render(request, 'ra/view.html', {'appointment': appointment, 'student': student}, context_instance=RequestContext(request))

#View RA Appointment Form (PDF)
@requires_role("FUND")
def form(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug)
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename=%s.pdf' % (appointment.slug)
    ra_form(appointment, response)
    return response

@requires_role("FUND")
def letter(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug)
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename=%s-letter.pdf' % (appointment.slug)
    letter = OfficialLetter(response, unit=appointment.unit)
    contents = LetterContents(
        to_addr_lines=[], 
        from_name_lines=[appointment.hiring_faculty.first_name + " " + appointment.hiring_faculty.last_name,        appointment.unit.name], 
        salutation="Dear " + appointment.person.first_name, 
        closing="Yours Truly", 
        signer=appointment.hiring_faculty,
        cosigner_lines=['I agree to the conditions of employment', appointment.person.first_name + " " + appointment.person.last_name])
    paragraphs = [
        """This is to confirm remuneration of work performed as a Research Assistant from """ + appointment.start_date.strftime("%B %d, %Y") +  """ to """  + appointment.end_date.strftime("%B %d, %Y") + """, will be a Lump Sum payment of $""" + str(appointment.lump_sum_pay) + """.""",
        """Termination of this appointment may be initiated by either party giving one (1) week notice, except in the case of termination for cause.""",
        """This contract of employment exists solely between myself as recipient of research grant funds and your self. In no manner of form does this employment relationship extend to or affect Simon Fraser University in any way.""",
        """The primary purpose of this appointment is to assist you in furthering your education and the pursuit of your degree through the performance of research activities in your field of study. As such, payment for these activities will be classified as scholarship income for taxation purposes. Accordingly, there will be no income tax, CPP or EI deductions from income. You should set aside funds to cover your eventual income tax obligation; note that the first $3K total annual income from scholarship sources is not taxable.""",
        """Basic Benefits: further details are in SFU Policies and Procedures R 50.02, which can be found on the SFU website.""",
        """If you accept the terms of this appointment, please sign and return the enclosed copy of this letter, retaining the original for your records.""",
    ]
    contents.add_paragraphs(paragraphs)
    letter.add_letter(contents)
    letter.write()
    return response


#Methods relating to Account creation. These are all straight forward.
@requires_role("FUND")
def new_account(request):
    accountform = AccountForm(request.POST or None)
    #This restricts a user to only creating account for a unit to which they belong.
    accountform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    if request.method == 'POST':
        if accountform.is_valid():
            account = accountform.save()
            messages.success(request, 'Created account ' + str(account.account_number))
            return HttpResponseRedirect(reverse('ra.views.accounts_index'))
    return render(request, 'ra/new_account.html', {'accountform': accountform})

@requires_role("FUND")
def accounts_index(request):
    depts = Role.objects.filter(person__userid=request.user.username, role='FUND').values('unit_id')
    accounts = Account.objects.filter(unit__id__in=depts).order_by("account_number")
    return render(request, 'ra/accounts_index.html', {'accounts': accounts}, context_instance=RequestContext(request))

#@requires_role("FUND")
#def delete_account(request, account_slug):
#    account = get_object_or_404(Account, slug=account_slug)
#    messages.success(request, 'Deleted account ' + str(account.account_number))
#    account.delete()
#    return HttpResponseRedirect(reverse(accounts_index))

@requires_role("FUND")
def edit_account(request, account_slug):
    account = get_object_or_404(Account, slug=account_slug)
    if request.method == 'POST':
        accountform = AccountForm(request.POST, instance=account)
        if accountform.is_valid():
            accountform.save()
            messages.success(request, 'Updated account ' + str(account.account_number))
            return HttpResponseRedirect(reverse(accounts_index))
    else:
        accountform = AccountForm(instance=account)
        accountform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    return render(request, 'ra/edit_account.html', {'accountform': accountform, 'account': account}, context_instance=RequestContext(request))

#Project methods. Also straight forward.
@requires_role("FUND")
def new_project(request):
    projectform = ProjectForm(request.POST or None)
    #Again, the user should only be able to create projects for units that they belong to.
    projectform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    if request.method == 'POST':
        if projectform.is_valid():
            project = projectform.save()
            messages.success(request, 'Created project ' + str(project.project_number))
            return HttpResponseRedirect(reverse('ra.views.projects_index'))
    return render(request, 'ra/new_project.html', {'projectform': projectform})

@requires_role("FUND")
def projects_index(request):
    depts = Role.objects.filter(person__userid=request.user.username, role='FUND').values('unit_id')
    projects = Project.objects.filter(unit__id__in=depts).order_by("project_number")
    return render(request, 'ra/projects_index.html', {'projects': projects}, context_instance=RequestContext(request))

#@requires_role("FUND")
#def delete_project(request, project_slug):
#    project = get_object_or_404(Project, slug=project_slug)
#    messages.success(request, 'Deleted project ' + str(project.project_number))
#    project.delete()
#    return HttpResponseRedirect(reverse(projects_index))

@requires_role("FUND")
def edit_project(request, project_slug):
    project = get_object_or_404(Project, slug=project_slug)
    if request.method == 'POST':
        projectform = ProjectForm(request.POST, instance=project)
        if projectform.is_valid():
            projectform.save()
            messages.success(request, 'Updated project ' + str(project.project_number))
            return HttpResponseRedirect(reverse(projects_index))
    else:
        projectform = ProjectForm(instance=project)
        projectform.fields['unit'].choices = [(u.id, u.name) for u in request.units]
    return render(request, 'ra/edit_project.html', {'projectform': projectform, 'project': project}, context_instance=RequestContext(request))

@requires_role("FUND")
def search_scholarships_by_student(request, student_id):
    #check permissions
    roles = Role.all_roles(request.user.username)
    allowed = set(['FUND'])
    if not (roles & allowed):
        return ForbiddenResponse(request, "Not permitted to search scholarships by student.")
    scholarships = Scholarship.objects.filter(student__person__emplid=student_id)
    response = HttpResponse(mimetype="application/json")
    data = [{'value': s.pk, 'display': s.scholarship_type.unit.label + ": " + s.scholarship_type.name + " (" + s.start_semester.name + " to " + s.end_semester.name + ")"}  for s in scholarships]
    json.dump(data, response, indent=1)
    return response
