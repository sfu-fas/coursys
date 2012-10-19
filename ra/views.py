from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib import messages
from django.template.defaultfilters import date as datefilter
from django.conf import settings
from ra.models import RAAppointment, Project, Account
from ra.forms import RAForm, RASearchForm, AccountForm, ProjectForm, RALetterForm, RABrowseForm
from grad.forms import possible_supervisors
from coredata.models import Person, Role, Semester
from courselib.auth import requires_role, ForbiddenResponse
from courselib.search import find_userid_or_emplid
from grad.models import GradStudent, Scholarship
from dashboard.letters import ra_form, OfficialLetter, LetterContents
from django import forms

import json, datetime

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
            return render(request, 'ra/search.html', context)
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
    return render(request, 'ra/search.html', context)




#This is an index of all RA Appointments belonging to a given person.
@requires_role("FUND")
def student_appointments(request, userid):
    student = get_object_or_404(Person, find_userid_or_emplid(userid))
    appointments = RAAppointment.objects.filter(person=student, unit__in=request.units).order_by("-created_at")
    grads = GradStudent.objects.filter(person=student, program__unit__in=request.units)
    context = {'appointments': appointments, 'student': student,
               'grads': grads}
    return render(request, 'ra/student_appointments.html', context)

def _appointment_defaults(units, emplid=None):
    hiring_faculty_choices = possible_supervisors(units)
    unit_choices = [(u.id, u.name) for u in units]
    project_choices = [(p.id, unicode(p)) for p in Project.objects.filter(unit__in=units, hidden=False)]
    account_choices = [(a.id, unicode(a)) for a in Account.objects.filter(unit__in=units, hidden=False)]
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
            userid = raform.cleaned_data['person'].userid_or_emplid()
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
    semester = Semester.next_starting()
    student = get_object_or_404(Person, find_userid_or_emplid(userid))
    initial = {'person': student.emplid, 'start_date': semester.start, 'end_date': semester.end, 'hours': 70 }
    scholarship_choices, hiring_faculty_choices, unit_choices, project_choices, account_choices =_appointment_defaults(request.units, emplid=student.emplid)
    gss = GradStudent.objects.filter(person=student)
    if gss:
        gradstudent = gss[0]
        initial['sin'] = gradstudent.sin()
    
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

@requires_role("FUND")
def edit_letter(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug)  

    if request.method == 'POST':
        form = RALetterForm(request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Updated RA Letter Text for ' + appointment.person.first_name + " " + appointment.person.last_name)
            return HttpResponseRedirect(reverse(student_appointments, kwargs=({'userid': appointment.person.userid})))
    else:
        if not appointment.offer_letter_text:
            appointment.offer_letter_text = appointment.default_letter_text()
        form = RALetterForm(instance=appointment)
    
    context = {'appointment': appointment, 'form': form}
    return render(request, 'ra/edit_letter.html', context)


#View RA Appointment
@requires_role("FUND")
def view(request, ra_slug):
    appointment = get_object_or_404(RAAppointment, slug=ra_slug)
    student = appointment.person
    return render(request, 'ra/view.html', {'appointment': appointment, 'student': student})

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
        from_name_lines=[appointment.hiring_faculty.first_name + " " + appointment.hiring_faculty.last_name, appointment.unit.name], 
        salutation="Dear " + appointment.person.first_name, 
        closing="Yours Truly", 
        signer=appointment.hiring_faculty,
        cosigner_lines=['I agree to the conditions of employment', appointment.person.first_name + " " + appointment.person.last_name])
    contents.add_paragraphs(appointment.letter_paragraphs())
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
    accounts = Account.objects.filter(unit__id__in=depts, hidden=False).order_by("account_number")
    return render(request, 'ra/accounts_index.html', {'accounts': accounts})

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
    return render(request, 'ra/edit_account.html', {'accountform': accountform, 'account': account})

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
    projects = Project.objects.filter(unit__id__in=depts, hidden=False).order_by("project_number")
    return render(request, 'ra/projects_index.html', {'projects': projects})

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
    return render(request, 'ra/edit_project.html', {'projectform': projectform, 'project': project})

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

@requires_role("FUND")
def browse(request):
    units = request.units
    hiring_choices = [('all', 'All')] + possible_supervisors(units)
    project_choices = [('all', 'All')] + [(p.id, unicode(p)) for p in Project.objects.filter(unit__in=units, hidden=False)]
    account_choices = [('all', 'All')] + [(a.id, unicode(a)) for a in Account.objects.filter(unit__in=units, hidden=False)]
    if 'data' in request.GET:
        # AJAX query for data
        ras = RAAppointment.objects.filter(unit__in=units) \
                .select_related('person', 'hiring_faculty', 'project', 'account')
        if 'hiring_faculty' in request.GET and request.GET['hiring_faculty'] != 'all':
            ras = ras.filter(hiring_faculty__id=request.GET['hiring_faculty'])
        if 'project' in request.GET and request.GET['project'] != 'all':
            ras = ras.filter(project__id=request.GET['project'], project__unit__in=units)
        if 'account' in request.GET and request.GET['account'] != 'all':
            ras = ras.filter(account__id=request.GET['account'], account__unit__in=units)

        truncated = False
        if ras.count() > 200:
            ras = ras[:200]
            truncated = True
        data = []
        for ra in ras:
            radata = {
                'slug': ra.slug,
                'name': ra.person.sortname(),
                'hiring': ra.hiring_faculty.sortname(),
                'project': unicode(ra.project),
                'account': unicode(ra.account),
                'start': datefilter(ra.start_date, settings.GRAD_DATE_FORMAT),
                'end': datefilter(ra.end_date, settings.GRAD_DATE_FORMAT),
                'amount': '$'+unicode(ra.lump_sum_pay),
                }
            data.append(radata)
        
        response = HttpResponse(mimetype="application/json")
        json.dump({'truncated': truncated, 'data': data}, response, indent=1)
        return response

    else:
        # request for page
        form = RABrowseForm()
        form.fields['hiring_faculty'].choices = hiring_choices
        form.fields['account'].choices = account_choices
        form.fields['project'].choices = project_choices
        context = {
            'form': form
            }
        return render(request, 'ra/browse.html', context)

def pay_periods(request):
    """
    Calculate number of pay periods between contract start and end dates.
    i.e. number of work days in period / 10
    
    I swear this was easier that doing it in JS, okay?
    """
    day = datetime.timedelta(days=1)
    week = datetime.timedelta(days=7)
    if 'start' not in request.GET or 'end' not in request.GET:
        result = ''
    else:
        st = request.GET['start']
        en = request.GET['end']
        try:
            st = datetime.datetime.strptime(st, "%Y-%m-%d").date()
            en = datetime.datetime.strptime(en, "%Y-%m-%d").date()
        except ValueError:
            result = ''
        else:
            # move start/end into Mon-Fri work week
            if st.weekday() == 5:
                en += 2*day
            elif st.weekday() == 6:
                en += day
            if en.weekday() == 5:
                en -= day
            elif en.weekday() == 6:
                en -= 2*day

            # number of full weeks (until sameday: last same weekday before end date)
            weeks = ((en-st)/7).days
            sameday = st + weeks*week
            assert sameday <= en < sameday + week
            
            # number of days remaining
            days = (en - sameday).days
            if sameday.weekday() > en.weekday():
                # don't count weekend days in between
                days -= 2
            
            days += 1 # count both start and end days
            result = "%.1f" % ((weeks*5 + days)/10.0)
    
    return HttpResponse(result, mimetype='text/plain;charset=utf-8')



