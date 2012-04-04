from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, get_list_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from django.conf import settings
from grad.models import GradStudent, GradProgram, Supervisor, GradRequirement, CompletedRequirement, GradStatus, \
        ScholarshipType, Scholarship, Promise, OtherFunding, LetterTemplate, \
    Letter
from grad.forms import SupervisorForm, PotentialSupervisorForm, GradAcademicForm, GradProgramForm, \
        GradStudentForm, GradStatusForm, GradRequirementForm, possible_supervisors, BaseSupervisorsFormSet, \
    SearchForm, LetterTemplateForm, LetterForm, UploadApplicantsForm, new_promiseForm, new_scholarshipForm,\
    new_scholarshipTypeForm, QuickSearchForm
from ta.models import TAContract, TAApplication, TACourse
#from ta.views import total_pay
from ra.models import RAAppointment
from coredata.models import Person, Role, Semester, CAMPUS_CHOICES
from coredata.queries import more_personal_info, SIMSProblem, GRADFIELDS
from django import forms
from django.forms.models import modelformset_factory, inlineformset_factory
from courselib.auth import requires_role, ForbiddenResponse, has_role
from courselib.search import get_query
import datetime, json
from django.contrib import messages
from log.models import LogEntry
from django.template.base import Template
from django.template.context import Context
import copy

from dashboard.letters import OfficialLetter, LetterContents
from django.contrib.auth.decorators import login_required


# get semester based on input datetime. defaults to today
# returns semseter object
def get_semester(date=datetime.date.today()):
    year = date.year
    next_sem = 0
    for s in Semester.objects.filter(start__year=year).order_by('-start'):
        if next_sem == 1:
            # take this semster
            return s
        if date >= s.start:
            if date <= s.end :
                return s
            else:
                #take the next semseter
                next_sem = 1

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
    supervisors = Supervisor.objects.filter(student=grad)
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
    supervisors = Supervisor.objects.filter(student=grad, position__gte=1).select_related('supervisor')
    supervisor_people = [s.supervisor for s in supervisors if s.supervisor]
    # Using filter because get returns an error when there are no matching queries
    pot_supervisor = Supervisor.objects.filter(student=grad, position=0) 
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
        if potential_supervisors_form.is_valid():
            #change gradstudent's last updated/by info to newest
            grad.updated_at = datetime.datetime.now()
            grad.created_by = request.user.username  
            grad.save()                
            superF = potential_supervisors_form.save(commit=False)
            superF.modified_by = request.user.username
            superF.student = grad #Passing grad student info to model
            superF.position = 0   #Hard coding potential supervisor and passing to model
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

    # set frontend defaults
    page_title = "%s's Supervisor(s) Record" % (grad.person.first_name)
    crumb = "%s, %s" % (grad.person.first_name, grad.person.last_name)
    gp = grad.person.get_fields 
    context = {
               'supervisors_formset': supervisors_formset,
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
    supervisors = Supervisor.objects.filter(student=grad, position__gte=1).select_related('supervisor')
    supervisor_people = [s.supervisor for s in supervisors if s.supervisor]
    if request.method == 'POST':
        supervisors_formset = modelformset_factory(Supervisor, form=SupervisorForm, formset=BaseSupervisorsFormSet)(request.POST, prefix="form")
        for f in supervisors_formset:
            f.set_supervisor_choices(possible_supervisors([grad.program.unit], extras=supervisor_people))
            f.fields['position'].widget = forms.HiddenInput()
        
        if supervisors_formset.is_valid():
            #change gradstudent's last updated info to newest
            grad.updated_at = datetime.datetime.now()
            grad.created_by = request.user.username  
            grad.save()
            for s in supervisors_formset:
                if (not s.cleaned_data['supervisor'] == None or s.cleaned_data['external'] == None):
                    s.instance.student = grad
                else:
                    s.cleaned_data = None
                    s._changed_data = []
                    
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
    
    if request.method == 'POST':
        grad_form = GradAcademicForm(request.POST, instance=grad, prefix="grad")
        if grad_form.is_valid():
            gradF = grad_form.save(commit=False)
            gradF.modified_by = request.user.username
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
        new_status_form = GradStatusForm(initial={'start': Semester.current()})

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
    
    ls = get_letter_dict(grad)
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
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad_slug}))
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

def get_letter_dict(grad):
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
        ls = get_letter_dict(grad)
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


@requires_role("GRAD")
def search(request):
    # clean out empty query args, mainly for debugging so it's easier to see what
    # search arguments are being passed
    if len(request.GET) > 0:
        cleaned_get = copy.copy(request.GET)
        for k, l in request.GET.iterlists():
            if len(filter(lambda x:len(x) > 0, l)) == 0:
                del cleaned_get[k]
        if len(cleaned_get) < len(request.GET):
            return HttpResponseRedirect(reverse(search) + '?' + cleaned_get.urlencode())
    # TODO: move the above code to a separate function
    
    if len(request.GET) == 0:
        form = SearchForm()
    else:
        form = SearchForm(request.GET)
    if form.is_valid():
        # if we store the query string in the database 
        #query_string = iri_to_uri(request.META.get('QUERY_STRING',''))
        
        #TODO: (1) finish constructing search query from form's data
        #TODO: (2) make a form and add column selection
        #TODO: (3) implement search saving (model, ui)
        
        query = form.get_query()
        grads = GradStudent.objects.filter(query).distinct()
        grads = filter(form.secondary_filter(), grads)
        # if performance becomes an issue, use this instead
        #grads = itertools.ifilter(form.secondary_filter, grads)
        # TODO get list of columns selected and send that seperately
        context = {
                   'page_title' : 'Graduate Student Search Results',
                   'crumb' : 'Grads',
                   'grads': grads,
                   }
        return render(request, 'grad/search_results.html', context)
    else:
        page_title = 'Graduate Student Advanced Search'
        context = {
                   'page_title' : page_title,
                   'form':form
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
        # ...
        print request.GET
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

@login_required
def student_financials(request):
    grad = get_object_or_404(GradStudent,person__userid=request.user.username)
    # TODO: Even though there should only be one grad, 
    # figure out the right grad student entry to use
    # in case there are multiple
    return HttpResponseRedirect(reverse('grad.views.financials',kwargs={'grad_slug':grad.slug})) 

#@requires_role("GRAD")
@login_required
def financials(request, grad_slug):
    curr_user = request.user
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    is_supervisor = False
    is_student = curr_user.username == grad.person.userid
    for supervisor in Supervisor.objects.filter(student=grad):
        if supervisor.supervisor.id == curr_user.username:
            is_supervisor = True
    
    if is_student or is_supervisor or has_role("GRAD",request):
        
        current_status = GradStatus.objects.get(student=grad, hidden=False, end=None)
        grad_status_qs = GradStatus.objects.filter(student=grad, status="ACTI")
        eligible_scholarships = ScholarshipType.objects.filter(eligible=True)
        scholarships_qs = Scholarship.objects.filter(student=grad)
        promises_qs = Promise.objects.filter(student=grad)
        other_fundings = OtherFunding.objects.filter(student=grad)
        
        applications = TAApplication.objects.filter(person=grad.person)
        contracts = TAContract.objects.filter(application__in=applications, status="ACC")
        appointments = RAAppointment.objects.filter(person=grad.person)       
        
        
        # initialize earliest starting and latest ending semesters for display. 
        # Falls back on current semester if none 
        earliest_semester = get_semester() # set earliest semester as current semester
        latest_semester = get_semester()   # set latest semester as current semester
        
        for status in grad_status_qs:
            if(earliest_semester > status.start):
                earliest_semester = status.start
            if(latest_semester < status.start):
                latest_semester = status.start
        for promise in promises_qs:
            if(earliest_semester > promise.start_semester):
                earliest_semester = promise.start_semester
            if(latest_semester < promise.end_semester):
                latest_semester = promise.end_semester
        for scholarship in scholarships_qs:
            if(earliest_semester > scholarship.start_semester):
                earliest_semester = scholarship.start_semester
            if(latest_semester < scholarship.end_semester):
                latest_semester = scholarship.end_semester
        for other_funding in other_fundings:
            if(earliest_semester > other_funding.semester):
                earliest_semester = other_funding.semester 
            if(latest_semester < other_funding.semester):
                latest_semester = other_funding.semester
        for contract in contracts:
            if(earliest_semester > contract.posting.semester):
                earliest_semester = contract.posting.semester
            if(latest_semester < contract.posting.semester):
                latest_semester = contract.posting.semester 
        for appointment in appointments:
            app_start_sem = get_semester(appointment.start_date)
            app_end_sem = get_semester(appointment.end_date)
            if(earliest_semester > app_start_sem):
                earliest_semester = app_start_sem
            if(latest_semester < app_end_sem):
                latest_semester = app_end_sem
    
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
            for semester_other_funding in semester_other_fundings:
                if semester_other_funding.eligible == True:
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
            
            ta_ra = {}
            type = ""
            courses = []
            amount = 0
            for contract in contracts:
                if contract.posting.semester == semester:
                    type = "TA"
                    for course in TACourse.objects.filter(contract=contract):
                        courses.append({'course':course.course,'amount': course.pay()})
                    
            for appointment in appointments:
                app_start_sem = get_semester(appointment.start_date)
                app_end_sem = get_semester(appointment.end_date)
                if app_start_sem >= semester and app_end_sem <= semester:
                    type = "RA"
                    amount = appointment.lump_sum_pay
                    courses.append({'course':"RA - %s" % appointment.project, 'amount':amount })
            
            ta_ra['type'] = type
            ta_ra['courses'] = courses
            ta_ra['amount'] = amount
            
            scholarships_in_semester['semester_total'] += amount
            
            semesters.append({'semester':semester, 'status':status,'scholarship_details':scholarships_in_semester, 'promise':promise, 'promised_amount':semester_promised_amount,'owing':semester_owing, 'ta_ra': ta_ra})
    
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
    else:
        return ForbiddenResponse(request, 'You do not have sufficient permission to access this page') 
    
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
        temp = get_semester
        print "semester"
        print temp
        promise_form = new_promiseForm(initial={'start_semester': get_semester(), 'amount':'$0.00'})

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
        temp = get_semester
        print "semester"
        print temp
        scholarship_form = new_scholarshipForm(initial={'student':grad,'start_semester':get_semester(),'amount':'$0.00'})

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