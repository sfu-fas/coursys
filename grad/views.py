from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, get_list_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from grad.models import GradStudent, GradProgram, Supervisor, GradRequirement, CompletedRequirement, GradStatus, \
        ScholarshipType, Scholarship, Promise, OtherFunding, LetterTemplate, \
        Letter, STATUS_ACTIVE, SavedSearch
from grad.forms import SupervisorForm, PotentialSupervisorForm, GradAcademicForm, GradProgramForm, \
        GradStudentForm, GradStatusForm, GradRequirementForm, possible_supervisors, BaseSupervisorsFormSet, \
    SearchForm, LetterTemplateForm, LetterForm, UploadApplicantsForm, new_promiseForm, new_scholarshipForm,\
    new_scholarshipTypeForm, QuickSearchForm, SaveSearchForm
from ta.models import TAContract, TAApplication, TACourse
#from ta.views import total_pay
from ra.models import RAAppointment
from coredata.models import Person, Role, Semester, CAMPUS_CHOICES
from coredata.queries import more_personal_info, SIMSProblem, GRADFIELDS
from django import forms
from django.forms.models import modelformset_factory, inlineformset_factory
from courselib.auth import requires_role, ForbiddenResponse, has_role,\
    NotFoundResponse
from courselib.search import get_query
import datetime, json
from django.contrib import messages
from log.models import LogEntry
from django.template.base import Template
from django.template.context import Context
import copy, itertools

from dashboard.letters import OfficialLetter, LetterContents
from django.contrib.auth.decorators import login_required

get_semester = Semester.get_semester

@requires_role("GRAD")
def index(request):
    form = QuickSearchForm()
    context = {'units': request.units, 'form': form}
    return render(request, 'grad/index.html', context)

@requires_role("GRAD")
def quick_search(request):
    if 'term' in request.GET:
        term = request.GET['term']
        grads = GradStudent.objects.filter(program__unit__in=request.units) \
                .filter(get_query(term, ['person__userid', 'person__emplid', 'person__first_name', 'person__last_name', 'person__pref_first_name',
                                         'program__label', 'program__description'])) \
                .select_related('person', 'program')[:50]
        data = [{'value': str(g.slug), 'label': "%s, %s" % (g.person.name(), g.program.label)} for g in grads]
        response = HttpResponse(mimetype='application/json')
        json.dump(data, response, indent=1)
        return response
    elif 'search' in request.GET:
        grad_slug = request.GET['search']
        return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad_slug}))
    else:
        return ForbiddenResponse(request, 'must send term')


@requires_role("GRAD")
def view_all(request, grad_slug):
    # will display academic, personal, FIN, status history, supervisor
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    supervisors = Supervisor.objects.filter(student=grad, removed=False)
    status_history = GradStatus.objects.filter(student=grad, hidden=False)
    letter = Letter.objects.filter(student=grad)
    #calculate missing reqs
    completed_req = CompletedRequirement.objects.filter(student=grad)
    req = GradRequirement.objects.filter(program=grad.program)
    missing_req = req    
    for s in completed_req:
        missing_req = missing_req.exclude(description=s.requirement.description)
    
    # set frontend defaults

    gp = grad.person.get_fields
    context = {
               'grad' : grad,
               'gp' : gp,
               'status_history' : status_history,
               'supervisors' : supervisors,
               'completed_req' : completed_req,
               'missing_req' : missing_req,
               'letter' : letter         
               }
    return render(request, 'grad/view_all.html', context)

@requires_role('GRAD')
def grad_more_info(request, grad_slug):
    """
    AJAX request for contact info, etc. (queries SIMS directly)
    """
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    try:
        data = more_personal_info(grad.person.emplid, exclude=GRADFIELDS)
    except SIMSProblem as e:
        data = {'error': e.message}
    
    response = HttpResponse(mimetype='application/json')
    json.dump(data, response, indent=1)
    return response


@requires_role("GRAD")
def manage_supervisors(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    supervisors = Supervisor.objects.filter(student=grad, supervisor_type__in=['SEN','COM'], removed=False).select_related('supervisor')
    supervisor_people = [s.supervisor for s in supervisors if s.supervisor]
    # Using filter because get returns an error when there are no matching queries
    pot_supervisor = Supervisor.objects.filter(student=grad, removed=False, supervisor_type='POT') 
    # Initialize potential supervisor to first on of the list of results
    # There should be exactly one match unless there is data error
    extra_form = 0
    if(supervisors.count() == 0):
        extra_form = 1
    if (pot_supervisor.count() == 0):
        pot_supervisor = None
    else:
        pot_supervisor = pot_supervisor[0]
        
    supervisors_formset = modelformset_factory(Supervisor, form=SupervisorForm, extra=extra_form, max_num=4)(queryset=supervisors, prefix="form")
    for f in supervisors_formset:
        f.set_supervisor_choices(possible_supervisors([grad.program.unit], extras=supervisor_people))
        f.fields['position'].widget = forms.HiddenInput()
        if(extra_form == 1):
            f.fields['position'].initial = 1

    if request.method == 'POST':
        potential_supervisors_form = PotentialSupervisorForm(request.POST, instance=pot_supervisor, prefix="pot_sup")
        potential_supervisors_form.set_supervisor_choices(possible_supervisors([grad.program.unit]))
        if potential_supervisors_form.is_valid():
            #change gradstudent's last updated/by info to newest
            grad.updated_at = datetime.datetime.now()
            grad.created_by = request.user.username  
            grad.save()                
            superF = potential_supervisors_form.save(commit=False)
            superF.modified_by = request.user.username
            superF.student = grad #Passing grad student info to model
            superF.position = 0   #Hard coding potential supervisor and passing to model
            superF.supervisor_type = 'POT'
            superF.save()
            messages.success(request, "Updated Potential Supervisor for %s." % (potential_supervisors_form.instance.student))
            l = LogEntry(userid=request.user.username,
                  description="Updated Potential Supervisor for %s." % (potential_supervisors_form.instance.student),
                  related_object=potential_supervisors_form.instance)
            l.save()              
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad_slug}))
    else:
        potential_supervisors_form = PotentialSupervisorForm(instance=pot_supervisor, prefix="pot_sup")
        potential_supervisors_form.set_supervisor_choices(possible_supervisors([grad.program.unit]))

    # check for co-senior supervisor
    second = supervisors.filter(position=2)
    second_co = False
    if second:
        second_co = second[0].supervisor_type=='SEN'

    # set frontend defaults
    page_title = "%s's Supervisor(s) Record" % (grad.person.first_name)
    crumb = "%s, %s" % (grad.person.first_name, grad.person.last_name)
    gp = grad.person.get_fields 
    context = {
               'supervisors_formset': supervisors_formset,
               'second_co': second_co,
               'potential_supervisors_form': potential_supervisors_form,
               'page_title' : page_title,
               'crumb' : crumb,
               'grad' : grad,
               'gp' : gp,
               }
    return render(request, 'grad/manage_supervisors.html', context)

@requires_role("GRAD")
def update_supervisors(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    supervisors = Supervisor.objects.filter(student=grad, supervisor_type__in=['SEN','COM'], removed=False).select_related('supervisor')
    supervisor_people = [s.supervisor for s in supervisors if s.supervisor]
    if request.method == 'POST':
        supervisors_formset = modelformset_factory(Supervisor, form=SupervisorForm, formset=BaseSupervisorsFormSet)(request.POST, prefix="form")
        for f in supervisors_formset:
            f.set_supervisor_choices(possible_supervisors([grad.program.unit], extras=supervisor_people))
            f.fields['position'].widget = forms.HiddenInput()
        
        if supervisors_formset.is_valid():
            second_co = 'second-co' in request.POST # is second supervisor is co-senior checked?
            #change gradstudent's last updated info to newest
            grad.updated_at = datetime.datetime.now()
            grad.created_by = request.user.username  
            grad.save()
            for s in supervisors_formset:
                # infer supervisor_type from other fields we have
                s.instance.supervisor_type = 'SEN' if s.cleaned_data['position'] == 1 else 'COM'
                if second_co and 'position' in s.cleaned_data and s.cleaned_data['position'] == 2:
                    s.instance.supervisor_type = 'SEN'

                s.instance.student = grad
            
            supervisors_formset.save()
                    
            messages.success(request, "Updated Supervisor(s) for %s." % (grad))
            l = LogEntry(userid=request.user.username,
                  description="Updated Supervisor(s) for %s." % (grad),
                  related_object=grad)
            l.save()
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad_slug}))
        else:
            page_title = "%s's Supervisor(s) Record" % (grad.person.first_name)
            crumb = "%s, %s" % (grad.person.first_name, grad.person.last_name)
            gp = grad.person.get_fields 
            context = {
               'supervisors_formset': supervisors_formset,
               #'potential_supervisors_form': potential_supervisors_form,
               'page_title' : page_title,
               'crumb' : crumb,
               'grad' : grad,
               'gp' : gp,
               }
            return render(request, 'grad/manage_supervisors.html', context)
            #return HttpResponseRedirect(reverse(manage_supervisors, kwargs={'grad_slug':grad_slug}))

    else:
        return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug': grad_slug}))

@requires_role("GRAD")
def manage_requirements(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)    
    
    #calculate/find missing reqs
    completed_req = CompletedRequirement.objects.filter(student=grad)
    req = GradRequirement.objects.filter(program=grad.program)
    req_choices = [(u'', u'\u2014')] + [(r.id, r.description) for r in req]
    missing_req = req    
    for s in completed_req:
        missing_req = missing_req.exclude(description=s.requirement.description)
    num_missing = req.count()
    
    ReqFormSet = inlineformset_factory(GradStudent, CompletedRequirement, max_num=num_missing, can_order=False) 
    if request.method == 'POST':
        req_formset = ReqFormSet(request.POST, request.FILES, instance=grad, prefix='req')
        for f in req_formset:
            f.fields['requirement'].choices = req_choices 

        if req_formset.is_valid():
            #change gradstudent's last updated info to newest
            grad.updated_at = datetime.datetime.now()
            grad.created_by = request.user.username            
            grad.save()
            req_formset.save()
            messages.success(request, "Updated Grad Requirements for %s." % (req_formset.instance.person))
            l = LogEntry(userid=request.user.username,
                  description="Updated Grad Requirements for %s." % (req_formset.instance.person),
                  related_object=req_formset.instance)
            l.save()   
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad_slug}))
    else:
        req_formset = ReqFormSet(instance=grad, prefix='req')
        for f in req_formset:
            f.fields['requirement'].choices = req_choices

    # set frontend defaults
    page_title = "%s's Requirements Record" % (grad.person.first_name)
    crumb = "%s, %s" % (grad.person.first_name, grad.person.last_name)
    gp = grad.person.get_fields     
    context = {
               'req_formset': req_formset,
               'page_title' : page_title,
               'crumb' : crumb,
               'gp' : gp,
               'grad' : grad,
               'missing_req' : missing_req     
               }
    return render(request, 'grad/manage_requirements.html', context)


@requires_role("GRAD")
def manage_academics(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    program_choices = [(p.id, unicode(p)) for p in GradProgram.objects.filter(unit__in=request.units)]
    
    if request.method == 'POST':
        grad_form = GradAcademicForm(request.POST, instance=grad, prefix="grad")
        grad_form.fields['program'].choices = program_choices
        if grad_form.is_valid():
            gradF = grad_form.save(commit=False)
            gradF.modified_by = request.user.username
            gradF.slug = None
            grad.slug = None
            gradF.save()
            messages.success(request, "Updated Grad Academics for %s." % (grad_form.instance.person))
            l = LogEntry(userid=request.user.username,
                  description="Updated Grad Academics for %s." % (grad_form.instance.person),
                  related_object=grad_form.instance)
            l.save()    
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad.slug}))
    else:
        grad_form = GradAcademicForm(instance=grad, prefix="grad")
        grad_form.fields['program'].choices = program_choices

    # set frontend defaults
    page_title = "%s 's Graduate Academic Record" % (grad.person.first_name)
    crumb = "%s, %s" % (grad.person.first_name, grad.person.last_name)
    gp = grad.person.get_fields 
    context = {
               'grad_form': grad_form,
               'page_title' : page_title,
               'crumb' : crumb,
               'grad' : grad,
               'gp' : gp,
               }
    return render(request, 'grad/manage_academics.html', context)


@requires_role("GRAD")
def manage_status(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    status_history = get_list_or_404(GradStatus, student=grad.id, hidden=False)

    if request.method == 'POST':
        new_status_form = GradStatusForm(request.POST)
        if new_status_form.is_valid():
            # Save new status
            new_actual_status = new_status_form.save(commit=False)
            new_actual_status.student = grad
            new_actual_status.save()
            
            #change gradstudent's last updated/by info to newest
            grad.updated_at = datetime.datetime.now()
            grad.created_by = request.user.username
            grad.save()
            
            messages.success(request, "Updated Status History for %s." % (grad.person))
            l = LogEntry(userid=request.user.username,
                    description="Updated Status History for %s." % (grad.person),
                    related_object=new_status_form.instance)
            l.save()                       
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad_slug}))
    else:
        new_status_form = GradStatusForm(initial={'start': Semester.current(), 'start_date': datetime.date.today()})

    # set frontend defaults
    page_title = "%s 's Status Record" % (grad.person.first_name)
    crumb = "%s, %s" % (grad.person.first_name, grad.person.last_name)
    gp = grad.person.get_fields
    context = {
               'new_status' : new_status_form,
               'status_history' : status_history,
               'page_title' : page_title,
               'crumb' : crumb,
               'grad' : grad,
               'gp' : gp
               }
    return render(request, 'grad/manage_status.html', context)
    
@requires_role("GRAD")
def new(request):
    if request.method == 'POST':
        grad_form = GradStudentForm(request.POST, prefix="grad")
        supervisors_form = PotentialSupervisorForm(request.POST, prefix="sup")
        status_form = GradStatusForm(request.POST, prefix="stat")
        if grad_form.is_valid() and supervisors_form.is_valid() and status_form.is_valid() :
            gradF = grad_form.save(commit=False)
            gradF.created_by = request.user.username
            gradF.save()
            superF = supervisors_form.save(commit=False)
            supervisors_form.cleaned_data["student"] = gradF
            superF.student_id = gradF.id
            superF.position = 0
            superF.created_by = request.user.username
            supervisors_form.save()
            statusF = status_form.save(commit=False)
            status_form.cleaned_data["student"] = gradF
            statusF.created_by = request.user.username
            statusF.student_id = gradF.id
            status_form.save()
            messages.success(request, "Created new grad student %s." % (grad_form.instance.person))
            l = LogEntry(userid=request.user.username,
                  description="Created new grad student %s." % (grad_form.instance.person),
                  related_object=grad_form.instance)
            l.save()           
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':gradF.slug}))
    else:
        prog_list = get_list_or_404(GradProgram)
        grad_form = GradStudentForm(prefix="grad", initial={'program': prog_list[0], 'campus': CAMPUS_CHOICES[0][0] })
        supervisors_form = PotentialSupervisorForm(prefix="sup",)  
        status_form = GradStatusForm(prefix="stat", initial={'status': 'ACTI', 'start': get_semester() })  
        
        #initial: 'start' returns nothing if there are no future semester available in DB 

    # set frontend defaults
    page_title = 'New Graduate Student Record'
    crumb = 'New Grad' 
    context = {
               'grad_form': grad_form,
               #'req_form': req_form,
               'supervisors_form': supervisors_form,
               'status_form': status_form,
               'page_title' : page_title,
               'crumb' : crumb
               }
    return render(request, 'grad/new.html', context)

@requires_role("GRAD")
def new_program(request):
    unit_choices = [(u.id, u.name) for u in request.units]
    if request.method == 'POST':
        form = GradProgramForm(request.POST)
        form.fields['unit'].choices = unit_choices 
        if form.is_valid():
            form.save()
            messages.success(request, "Created new program %s for %s." % (form.instance.label, form.instance.unit))
            l = LogEntry(userid=request.user.username,
                  description="Created new program %s for %s." % (form.instance.label, form.instance.unit),
                  related_object=form.instance)
            l.save()                        
            return HttpResponseRedirect(reverse(programs))
    else:
        form = GradProgramForm()    
        form.fields['unit'].choices = unit_choices

    page_title = 'New Program'  
    crumb = 'New Program' 
    context = {
               'form': form,
               'page_title' : page_title,
               'crumb' : crumb
               }
    return render(request, 'grad/new_program.html', context)

@requires_role("GRAD")
def programs(request):
    programs = GradProgram.objects.filter(unit__in=request.units)
    
    # set frontend defaults
    page_title = 'Graduate Programs Records'
    crumb = 'Grad Programs' 
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'programs': programs               
               }
    return render(request, 'grad/programs.html', context)

@requires_role("GRAD")
def requirements(request):
    requirements = GradRequirement.objects.filter(program__unit__in=request.units)

    page_title = 'Graduate Requirements'
    crumb = 'Grad Requirements'     
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'requirements': requirements                 
               }
    return render(request, 'grad/requirements.html', context)

@requires_role("GRAD")
def new_requirement(request):
    program_choices = [(p.id, p.label) for p in GradProgram.objects.filter(unit__in=request.units)]
    if request.method == 'POST':
        form = GradRequirementForm(request.POST)
        form.fields['program'].choices = program_choices
        if form.is_valid():
            form.save()
            messages.success(request, "Created new grad requirement %s in %s." % (form.instance.description, form.instance.program))
            l = LogEntry(userid=request.user.username,
                  description="Created new grad requirement %s in %s." % (form.instance.description, form.instance.program),
                  related_object=form.instance)
            l.save()            
            return HttpResponseRedirect(reverse(requirements))
    else:
        form = GradRequirementForm()
        form.fields['program'].choices = program_choices

    page_title = 'New Requirement'  
    crumb = 'New Requirement' 
    context = {
               'form': form,
               'page_title' : page_title,
               'crumb' : crumb
               }
    return render(request, 'grad/new_requirement.html', context)

@requires_role("GRAD")
def import_applic(request):
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

            return HttpResponseRedirect(reverse(index))
    else:
        next_sem = Semester.next_starting()
        form = UploadApplicantsForm(initial={'semester': next_sem.id})
        form.fields['unit'].choices = unit_choices
        form.fields['semester'].choices = semester_choices

    context = {
               'form': form,
               }
    return render(request, 'grad/import_applic.html', context)

@requires_role("GRAD")
def letter_templates(request):
    templates = LetterTemplate.objects.filter(unit__in=request.units)

    page_title = 'Letter Templates'
    crumb = 'Letter Templates'     
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'templates': templates                 
               }
    return render(request, 'grad/letter_templates.html', context)

"""
List of tags
"""

LETTER_TAGS = {
               'title': 'Mr. Ms.',
               'first_name': 'applicant\'s first name',
               'last_name': 'applicant\'s last name',
               'address': 'includes street, city/province/postal, country',
               'empl_data': 'type of employment RA, TA',
               'fund_type': 'RA, TA, Scholarship',
               'fund_amount_sem': 'amount of money paid per semester',
               'his_her' : '"his" or "her"',
               'program': 'program enrolled in',
               'first_season': 'semster when grad will begin his studies; fall, summer, spring',
               'first_year': 'year to begin; 2011',
               'first_month': 'month to begin; September'
               }

@requires_role("GRAD")
def new_letter_template(request):
    unit_choices = [(u.id, u.name) for u in request.units]
    if request.method == 'POST':
        form = LetterTemplateForm(request.POST)
        form.fields['unit'].choices = unit_choices 
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = request.user.username            
            f.save()
            messages.success(request, "Created new letter template %s for %s." % (form.instance.label, form.instance.unit))
            l = LogEntry(userid=request.user.username,
                  description="Created new letter template %s for %s." % (form.instance.label, form.instance.unit),
                  related_object=form.instance)
            l.save()            
            return HttpResponseRedirect(reverse(letter_templates))
    else:
        form = LetterTemplateForm()
        form.fields['unit'].choices = unit_choices 

    page_title = 'New Letter Template'  
    crumb = 'New'
    lt = sorted(LETTER_TAGS.iteritems()) 
    context = {
               'form': form,
               'page_title' : page_title,
               'crumb' : crumb,
               'LETTER_TAGS' : lt
               }
    return render(request, 'grad/new_letter_template.html', context)

@requires_role("GRAD")
def manage_letter_template(request, letter_template_slug):
    unit_choices = [(u.id, u.name) for u in request.units]    
    letter_template = get_object_or_404(LetterTemplate, slug=letter_template_slug)
    if request.method == 'POST':
        form = LetterTemplateForm(request.POST, instance=letter_template)
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = request.user.username            
            f.save()
            messages.success(request, "Updated %s letter for %s." % (form.instance.label, form.instance.unit))
            l = LogEntry(userid=request.user.username,
                  description="Updated new %s letter for %s." % (form.instance.label, form.instance.unit),
                  related_object=form.instance)
            l.save()            
            return HttpResponseRedirect(reverse(letter_templates))
    else:
        form = LetterTemplateForm(instance=letter_template)
        form.fields['unit'].choices = unit_choices 

    page_title = 'Manage Letter Template'  
    crumb = 'Manage' 
    lt = sorted(LETTER_TAGS.iteritems())
    context = {
               'form': form,
               'page_title' : page_title,
               'crumb' : crumb,
               'letter_template' : letter_template,
               'LETTER_TAGS' : lt
               }
    return render(request, 'grad/manage_letter_template.html', context)

@requires_role("GRAD")
def letters(request):
    letters = Letter.objects.filter(template__unit__in=request.units)

    page_title = 'All Letters'
    crumb = 'Letters'     
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'letters': letters                 
               }
    return render(request, 'grad/letters.html', context)


@requires_role("GRAD")
def view_all_letters(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    letters = Letter.objects.filter(student=grad)

    page_title = 'Letters for ' + grad.person.last_name + "," + grad.person.first_name
    crumb = 'Letters'     
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'letters': letters,
               'grad' : grad                 
               }
    return render(request, 'grad/letters.html', context)

@requires_role("GRAD")
def new_letter(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    templates = LetterTemplate.objects.filter(unit=grad.program.unit)
    from_choices = [('', u'\u2014')] + [(r.person.id, "%s, %s" % (r.person.name(), r.get_role_display()))
                                        for r in Role.objects.filter(unit=grad.program.unit)]
    directors = Role.objects.filter(unit=grad.program.unit, role='GRPD').order_by('-id')
    if directors:
        default_from = directors[0].person.id
    else:
        default_from = None
    
    ls = _get_letter_dict(grad)
    if request.method == 'POST':
        form = LetterForm(request.POST)
        form.fields['from_person'].choices = from_choices
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = request.user.username
            f.config = ls
            f.save()
            messages.success(request, "Created new %s letter for %s." % (form.instance.template.label, form.instance.student))
            l = LogEntry(userid=request.user.username,
                  description="Created new %s letter for %s." % (form.instance.template.label, form.instance.student),
                  related_object=form.instance)
            l.save()            
            return HttpResponseRedirect(reverse(view_all_letters, kwargs={'grad_slug':grad_slug}))
    else:
        form = LetterForm(initial={'student': grad, 'date': datetime.date.today(), 'from_person': default_from})
        form.fields['from_person'].choices = from_choices
        

    page_title = 'New Letter'  
    crumb = 'New Letter' 
    context = {
               'form': form,
               'page_title' : page_title,
               'crumb' : crumb,
               'grad' : grad,
               'templates' : templates
               }
    return render(request, 'grad/new_letter.html', context)

def _get_letter_dict(grad):
    gender = grad.person.gender()
    title = grad.person.title()
    first_name = grad.person.first_name
    last_name = grad.person.last_name
    addresses = grad.person.addresses()
    program = grad.program.description

    if 'home' in addresses:
        address = addresses['home']
    elif 'work' in addresses:
        address = addresses['work']
    else:
        address = ''

    if gender == "M" :
        hisher = "his"
    elif gender == "F":
        hisher = "her"
    else:
        hisher = "his/her"
        
    ls = {
            'title' : title,
            'his_her' : hisher,
            'first_name': first_name,
            'last_name': last_name,
            'address':  address,
            'empl_data': "OO type of employment RA, TA OO",
            'fund_type': "OO RA / TA / Scholarship]]",
            'fund_amount_sem': "OO amount of money paid per semester OO",
            'program': program,
            'first_season': "OO semster when grad will begin his studies; fall, summer, spring OO",
            'first_year': "OO year to begin; 2011 OO",
            'first_month': "OO month to begin; September OO"
          }
    return ls
"""
Get the text from letter template
"""
@requires_role("GRAD")
def get_letter_text(request, grad_slug, letter_template_id):
    text = ""
    grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
    if False and "{}" in str(grad.person.config):
        text = "There are no configs found in the student's profile.\n Please update profile in order to get templates to work."
    else: 
        lt = get_object_or_404(LetterTemplate, id=letter_template_id)
        temp = Template(lt.content)
        ls = _get_letter_dict(grad)
        text = temp.render(Context(ls))

    return HttpResponse(text)

@requires_role("GRAD")
def get_addresses(request):
    if 'id' not in request.GET:
        return ForbiddenResponse(request, 'must send id')
    sid = request.GET['id']
    grad = get_object_or_404(GradStudent, id=sid, program__unit__in=request.units)
    emplid = grad.person.emplid
    
    try:
        data = more_personal_info(emplid, needed=['addresses'])
    except SIMSProblem as e:
        data = {'error': e.message}
        
    resp = HttpResponse(mimetype="application/json")
    json.dump(data, resp, indent=1)
    return resp

from pages.models import _normalize_newlines
@requires_role("GRAD")
def get_letter(request, letter_slug):
    letter = get_object_or_404(Letter, slug=letter_slug, student__program__unit__in=request.units)
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename=%s.pdf' % (letter_slug)

    doc = OfficialLetter(response, unit=letter.student.program.unit)
    l = LetterContents(to_addr_lines=letter.to_lines.split("\n"), from_name_lines=letter.from_lines.split("\n"), date=letter.date, salutation=letter.salutation,
                 closing=letter.closing, signer=letter.from_person)
    content_text = _normalize_newlines(letter.content.rstrip())
    content_lines = content_text.split("\n\n")
    l.add_paragraphs(content_lines)
    doc.add_letter(l)
    doc.write() 
    return response


@requires_role("GRAD")
def view_letter(request, letter_slug):
    letter = get_object_or_404(Letter, slug=letter_slug)
    grad = get_object_or_404(GradStudent, person=letter.student.person)

    page_title = 'View Letter'  
    crumb = 'View' 
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'letter' : letter,
               'grad' : grad
               }
    return render(request, 'grad/view_letter.html', context)

def _get_cleaned_get(request):
    cleaned_get = copy.copy(request.GET)
    for k, l in request.GET.iterlists():
        if len(filter(lambda x:len(x) > 0, l)) == 0:
            del cleaned_get[k]
    return cleaned_get

@requires_role("GRAD")
def search(request):
    # Possible TODOs for search:
    # TODO: make groups of search fields collapsible
        # use field lists like SearchForm.semester_range_fields to organize the fields
        # into groups, like Dates, Student Status, Academics, Financials and Personal Details
        # and put the groups into separate divs, with headers, and use jquery.collapsible
        # on each of the groups
        # also this should allow the user to replace the loaded savedsearch with a new one
    # TODO: allow loading a saved search into the search form
        # make a new view for this purpose, or separate the results view into its own
        # just 'copy' (aka refactor by splitting up and follow DRY) this search view to just 
        # load the searchform with the savedsearch query as initial
    current_user = Person.objects.get(userid=request.user.username)
    query_string = request.META.get('QUERY_STRING','')
    try:
        savedsearch = SavedSearch.objects.get(person=current_user, query=query_string)
    except SavedSearch.DoesNotExist:
        savedsearch = None
    if savedsearch is None:
        if len(request.GET) > 0:
            cleaned_get = _get_cleaned_get(request)
            if len(cleaned_get) < len(request.GET):
                return HttpResponseRedirect(reverse(search) + u'?' + cleaned_get.urlencode())
        try:
            savedsearch = SavedSearch.objects.get(person=current_user, query=query_string)
        except SavedSearch.DoesNotExist:
            savedsearch = None
    
    form = SearchForm() if len(request.GET) == 0 else SearchForm(request.GET)
    
    if form.is_valid():
        query = form.get_query()
        grads = GradStudent.objects.filter(query).distinct()
        grads = filter(form.secondary_filter(), grads)
        # if performance becomes an issue, use this instead
        #grads = itertools.ifilter(form.secondary_filter, grads)
        # TODO get list of columns selected and send that seperately
        
        if savedsearch is not None:
            saveform = SaveSearchForm(instance=savedsearch)
        else:
            saveform = SaveSearchForm(initial={'person':current_user, 'query':query_string})
        
        columns = form.cleaned_data['columns']
        context = {
                   'grads': grads,
                   'columns': columns,
                   'saveform' : saveform,
                   }
        return render(request, 'grad/search_results.html', context)
    else:
        savedsearches = SavedSearch.objects.filter(person__in=(current_user,None))
        page_title = 'Graduate Student Advanced Search'
        context = {
                   'savedsearches' : savedsearches,
                   'page_title' : page_title,
                   'form':form,
                   'savedsearch' : savedsearch 
                   # a non-None savedsearch here means that somehow, an invalid search got saved
                   # the template gives the user the option to delete it
                   }
        return render(request, 'grad/search.html', context)

@requires_role("GRAD")
def search_results(request):
    """
    DataTables data for grad result display

    See: http://www.datatables.net/usage/server-side
    """
    if len(request.GET) == 0:
        form = SearchForm()
    else:
        form = SearchForm(request.GET)
    rows = []
    data = {}
    if form.is_valid():
        try:
            start = int(request.GET['iDisplayStart'])
            count = int(request.GET['iDisplayLength'])
        except (KeyError, ValueError):
            start = 0
            count = 200
        results = GradStudent.objects.filter(program__unit__in=request.units).select_related('person')
        total = results.count()
        results = list(results)
        results = results + results + results + results + results + results
        grads = results[start:start + count]
        for g in grads:
            rows.append([g.person.emplid])
        
        print rows
        data = {
                'iTotalRecords': total * 6,
                'aaData': rows,
                }
    if 'sEcho' in request.GET:
        data['sEcho'] = request.GET['sEcho']
    resp = HttpResponse(mimetype="application/json")
    json.dump(data, resp, indent=1)
    return resp

@requires_role("GRAD")
def save_search(request):
    current_user = Person.objects.get(userid=request.user.username)
    saveform = SaveSearchForm(request.POST)
    try:
        saveform.instance = SavedSearch.objects.get(
                person=saveform.data['person'], 
                query=saveform.data['query'])
    except SavedSearch.DoesNotExist:
        saveform.instance = SavedSearch(person=current_user)
    if saveform.is_valid():
        saveform.save()
        return HttpResponseRedirect(reverse(search))
    else:
        messages.add_message(request, messages.ERROR, saveform.errors.as_text())
        return HttpResponseRedirect(reverse(search) + u'?' + saveform.data['query'])

@requires_role("GRAD")
def delete_savedsearch(request):
    current_user = Person.objects.get(userid=request.user.username)
    if request.method != 'POST':
        return ForbiddenResponse(request)
    try:
        savedsearch = SavedSearch.objects.get(
                person=request.POST['person'], 
                query=request.POST['query'])
    except SavedSearch.DoesNotExist:
        return NotFoundResponse(request, u"This Saved Search doesn't exist.")
    if current_user != savedsearch.person:
        return ForbiddenResponse(request, u"You cannot delete this Saved Search.")
    savedsearch.delete()
    messages.add_message(request, messages.SUCCESS, u"Saved Search '%s' was successfully deleted." % savedsearch.name())
    return HttpResponseRedirect(reverse(search))

@login_required
def student_financials(request):
    grad = get_object_or_404(GradStudent, person__userid=request.user.username)
    # TODO: Even though there should only be one grad, 
    # figure out the right grad student entry to use
    # in case there are multiple
    return HttpResponseRedirect(reverse('grad.views.financials',kwargs={'grad_slug': grad.slug})) 

#@requires_role("GRAD")
@login_required
def financials(request, grad_slug):
    curr_user = request.user
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    is_student = curr_user.username == grad.person.userid    
    is_supervisor = Supervisor.objects.filter(student=grad, supervisor__userid=curr_user.username,
                                              supervisor_type='SEN', removed=False).count() > 0
    is_admin = Role.objects.filter(role='GRAD', unit=grad.program.unit, person__userid=curr_user.username).count()>0
    
    if not (is_student or is_supervisor or is_admin):
        return ForbiddenResponse(request, 'You do not have sufficient permission to access this page') 

    current_status = GradStatus.objects.filter(student=grad, hidden=False).order_by('-start')[0]
    grad_status_qs = GradStatus.objects.filter(student=grad, status__in=STATUS_ACTIVE)
    eligible_scholarships = ScholarshipType.objects.filter(eligible=True)
    scholarships_qs = Scholarship.objects.filter(student=grad)
    promises_qs = Promise.objects.filter(student=grad)
    other_fundings = OtherFunding.objects.filter(student=grad)
    
    #applications = TAApplication.objects.filter(person=grad.person)
    contracts = TAContract.objects.filter(application__person=grad.person, status="SGN").select_related('posting__semester')
    appointments = RAAppointment.objects.filter(person=grad.person)
    
    # initialize earliest starting and latest ending semesters for display. 
    # Falls back on current semester if none 
    all_semesters = itertools.chain( # every semester we have info for
                      [get_semester()],
                      (s.start for s in grad_status_qs),
                      (s.end for s in grad_status_qs),
                      (p.start_semester for p in promises_qs),
                      (p.end_semester for p in promises_qs),
                      (s.start_semester for s in scholarships_qs),
                      (s.end_semester for s in scholarships_qs),
                      (o.semester for o in other_fundings),
                      (c.posting.semester for c in contracts),
                      (get_semester(a.start_date) for a in appointments),
                      (get_semester(a.end_date) for a in appointments),
                    )
    all_semesters = itertools.ifilter(lambda x: isinstance(x, Semester), all_semesters)
    all_semesters = list(all_semesters)
    earliest_semester = min(all_semesters)
    latest_semester = max(all_semesters)

    semesters = []
    semesters_qs = Semester.objects.filter(start__gte=earliest_semester.start, end__lte=latest_semester.end).order_by('-name')

    for semester in semesters_qs:
        semester_total = 0
        scholarships_in_semester = {}
        semester_scholarships = scholarships_qs.filter(start_semester__lte=semester, end_semester__gte=semester)
        semester_eligible_scholarships = semester_scholarships.filter(scholarship_type__in=eligible_scholarships)
        semester_other_fundings = other_fundings.filter(semester=semester)
        
        s = []
        for ss in semester_scholarships:
            s.append({'scholarship':ss, 'semester_amount':ss.amount/(ss.end_semester-ss.start_semester+1)})
        scholarships_in_semester['scholarships'] = s
        
        scholarships_in_semester['other_funding'] = semester_other_fundings
        
        for semester_eligible_scholarship in semester_eligible_scholarships:
            if(semester_eligible_scholarship.start_semester != semester_eligible_scholarship.end_semester):
                semester_span = semester_eligible_scholarship.end_semester - semester_eligible_scholarship.start_semester + 1
                semester_total += semester_eligible_scholarship.amount/semester_span
            else:
                semester_total += semester_eligible_scholarship.amount
        for semester_other_funding in semester_other_fundings:
            if semester_other_funding.eligible:
                semester_total += semester_other_funding.amount
        scholarships_in_semester['semester_total'] = semester_total
        try:
            promise = promises_qs.get(start_semester__lte=semester,end_semester__gte=semester)
            semester_promised_amount = promise.amount/(promise.end_semester - promise.start_semester +1)
        except:
            promise = Promise.objects.none()
            semester_promised_amount = 0
        
         
        semester_owing = scholarships_in_semester['semester_total'] - semester_promised_amount
        
        status = None
        for s in GradStatus.objects.filter(student=grad):
            if s.start <= semester and (s.end == None or semester <= s.end) :
                status = s.get_status_display()
        
        ta_ra = []
        position_type = []
        
        amount = 0
        for contract in contracts:
            courses = []
            if contract.posting.semester == semester:
                position_type.append("TA")
                for course in TACourse.objects.filter(contract=contract):
                    amount += course.pay()
                    courses.append({'course':course.course,'amount': course.pay()})
                ta_ra.append({'type':"TA",'courses':courses,'amount':amount})
                
        for appointment in appointments:
            courses = []
            app_start_sem = get_semester(appointment.start_date)
            app_end_sem = get_semester(appointment.end_date)
            if app_start_sem <= semester and app_end_sem >= semester:
                position_type.append("RA")
                amount += appointment.lump_sum_pay
                courses.append({'course':"RA - %s" % appointment.project, 'amount':amount })
            ta_ra.append({'type':"RA",'courses':courses,'amount':amount})
        

        scholarships_in_semester['semester_total'] += amount
        
        semesters.append({'semester':semester, 'status':status,'scholarship_details':scholarships_in_semester,
                          'promise':promise, 'promised_amount':semester_promised_amount, 'owing':semester_owing,
                          'ta_ra': ta_ra, 'type': ', '.join(position_type)})

    promises = []
    for promise in promises_qs:
        received = 0
        for semester in semesters:
            if promise == semester.get('promise'):
                received += semester.get('scholarship_details').get('semester_total')
        owing = received - promise.amount
        
        # minor logic for display. 
        if owing < 0:
            owing = abs(owing)
        else:
            owing = -1
        
        promises.append({'promise':promise, 'received': received, 'owing': owing})

    # set frontend defaults
    page_title = "%s's Financial Summary" % (grad.person.first_name)
    crumb = "%s, %s" % (grad.person.last_name, grad.person.first_name)

    units = []
    try:
        units=request.units
    except:
        units = []

    context = {
               'semesters': semesters,
               'promises': promises,
               'page_title':page_title,
               'crumb':crumb,
               'grad':grad,
               'status': current_status,
               'unit': units,
               }
    return render(request, 'grad/view_financials.html', context)


@requires_role("GRAD")
def new_promise(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    if request.method == 'POST':
        promise_form = new_promiseForm(request.POST)
        if promise_form.is_valid():
            temp = promise_form.save(commit=False)
            temp.student = grad
            temp.save()
            messages.success(request, "Promise amount %s saved for %s." % (promise_form.cleaned_data['amount'], grad))
            
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad.slug}))
    else:
        promise_form = new_promiseForm(initial={'start_semester': get_semester().offset(1), 'end_semester': get_semester().offset(3), 'amount':'0.00'})

    page_title = "New Promise"
    crumb = "%s, %s" % (grad.person.last_name, grad.person.first_name)

    context = {'page_title':page_title,
                'crum':crumb,
                'grad':grad,
                'Promise_form': promise_form
    }
    return render(request, 'grad/manage_promise.html', context)

@requires_role("GRAD")
def manage_scholarship(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug = grad_slug)
    if request.method == 'POST':
        scholarship_form = new_scholarshipForm(request.POST)
        if scholarship_form.is_valid():
            temp = scholarship_form.save(commit=False)
            temp.student = grad
            temp.save()
            messages.success(request, "Scholarship for %s sucessfully saved." % (grad))
            
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad.slug}))
    else:
        scholarship_form = new_scholarshipForm(initial={'student':grad, 'start_semester':get_semester(), 'end_semester':get_semester(), 'amount':'0.00'})

    page_title = "New Scholarship"
    crumb = "%s, %s" % (grad.person.last_name, grad.person.first_name)

    context = {'page_title':page_title,
                'crumb':crumb,
                'grad':grad,
                'scholarship_form': scholarship_form
    }
    return render(request, 'grad/manage_scholarship.html', context)

@requires_role("GRAD")
def manage_scholarshipType(request):

    if request.method == 'POST':
        scholarshipType_form = new_scholarshipTypeForm(request.POST)
        if scholarshipType_form.is_valid():
            scholarshipType_form.save()
            messages.success(request, "Scholarship Type sucessfully saved.")
            
            return HttpResponseRedirect(reverse(index))
    else:
        scholarshipType_form = new_scholarshipTypeForm()

    page_title = "New Scholarship Type"
   
    context = {'page_title':page_title,
                'new_scholarshipTypeForm': scholarshipType_form
    }
    return render(request, 'grad/manage_scholarshipType.html', context)