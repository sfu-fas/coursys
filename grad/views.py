from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404, get_list_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from grad.forms import *
from coredata.models import Person, Role, Unit, Semester
from django.template import RequestContext
from django import forms
from django.forms.formsets import formset_factory
from courselib.auth import *
from django.core import serializers
from django.utils.safestring import mark_safe
import datetime

# get semester based on input datetime. defaults to today
# returns semseter object
def get_semester(date=datetime.date.today()):
    year = date.year
    next_sem = 0
    for s in Semester.objects.filter(start__year=year).order_by('-start'):
        if next_sem == 1:
            # take this semster
            return s
        if date > s.start:
            if date < s.end :
                return s
            else:
                #take the next semseter
                next_sem = 1
     

@requires_role("GRAD")
def index(request):
    grads = GradStudent.objects.all()
    
    # set frontend defaults
    page_title = 'Graduate Student Records'  
    crumb = 'Grads' 
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'grads': grads               
               }
    return render(request, 'grad/index.html', context)


@requires_role("GRAD")
def view_all(request, grad_slug):
    # will display academic, personal, FIN, status history, supervisor
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    supervisors = get_object_or_404(Supervisor, student=grad)
    status = get_list_or_404(GradStatus, student=grad)
    
    # set frontend defaults
    page_title = "%s 's Graduate Student Record" % (grad.person.first_name)
    crumb = "%s %s" % (grad.person.first_name, grad.person.last_name)
    gp = grad.person.get_fields 
    gr = grad.get_fields
    supervisors = supervisors.get_fields
    gs = [s.get_fields for s in status]
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'grad' : grad,
               'gp' : gp,
               'gr' : gr,
               'gs' : gs,
               'supervisors' : supervisors            
               }
    return render(request, 'grad/view_all.html', context)


@requires_role("GRAD")
def manage_supervisors(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    supervisors = get_object_or_404(Supervisor, student=grad)
    supervisors_formset = formset_factory(SupervisorForm, extra=1, max_num=4)()
    for f in supervisors_formset:
        f.fields['supervisor'].choices = possible_supervisors(grad.program.unit)

    if request.method == 'POST':
        potential_supervisors_form = PotentialSupervisorForm(request.POST, instance=supervisors, prefix="sup")
        if potential_supervisors_form.is_valid():
            potential_supervisors_form.save()
            superF = potential_supervisors_form.save(commit=False)
            superF.modified_by = request.user.username
            superF.save()            
            return HttpResponseRedirect(reverse(view_all, kwargs={'userid':userid} ))
    elif request.is_ajax():
        # TO DO: Update formset to correct number of forms displayed
        
        return HttpResponse("AJAX Completed") #return updated form.
    else:
        supervisors_form = SupervisorForm(instance=supervisors, prefix="sup") 
        potential_supervisors_form = PotentialSupervisorForm(instance=supervisors, prefix="sup")
        potential_supervisors_form.fields['supervisor'].choices = \
                possible_supervisors(grad.program.unit)

    # set frontend defaults
    page_title = "%s's Supervisor(s) Record" % (grad.person.first_name)
    crumb = "%s %s" % (grad.person.first_name, grad.person.last_name)
    gp = grad.person.get_fields 
    supervisors = supervisors.get_fields 
    context = {
               'supervisors_form': supervisors_form,
               'supervisors_formset': supervisors_formset,
               'potential_supervisors_form': potential_supervisors_form,
               'page_title' : page_title,
               'crumb' : crumb,
               'grad' : grad,
               'gp' : gp,
               'supervisors' : supervisors,
               }
    return render(request, 'grad/manage_supervisors.html', context)

@requires_role("GRAD")
def manage_academics(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    
    if request.method == 'POST':
        grad_form = GradAcademicForm(request.POST, instance=grad, prefix="grad")
        if grad_form.is_valid():
            gradF = grad_form.save(commit=False)
            gradF.modified_by = request.user.username
            gradF.save()
            return HttpResponseRedirect(reverse(index))
    else:
        grad_form = GradAcademicForm(instance=grad, prefix="grad")

    # set frontend defaults
    page_title = "%s 's Graduate Academic Record" % (grad.person.first_name)
    crumb = "%s %s" % (grad.person.first_name, grad.person.last_name)
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
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    gs = get_list_or_404(GradStatus, student=grad)
    status = gs[0]

    if request.method == 'POST':
        status_form = GradStatusForm(request.POST, instance=status, prefix="stat")
        if status_form.is_valid():
            status_form.save()
            return HttpResponseRedirect(reverse(index))
    else:
        status_form = GradStatusForm(instance=status, prefix="stat")

    # set frontend defaults
    page_title = "%s 's Status Record" % (grad.person.first_name)
    crumb = "%s %s" % (grad.person.first_name, grad.person.last_name)
    gp = grad.person.get_fields
    gs = [s.get_fields for s in gs]
    status = status.get_fields
    context = {
               'status_form': status_form,
               'page_title' : page_title,
               'crumb' : crumb,
               'grad' : grad,
               'gp' : gp,
               'gs' : gs,
               'status' : status
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
            return HttpResponseRedirect(reverse(index))
    else:
        grad_form = GradStudentForm(prefix="grad")
        supervisors_form = PotentialSupervisorForm(prefix="sup",)  
        status_form = GradStatusForm(prefix="stat", initial={'status': 'ACTI', 'start': get_semester() })  
        #initial: 'start' returns nothing if there are no future semester available in DB 

    # set frontend defaults
    page_title = 'New Graduate Student Record'
    crumb = 'New Grad' 
    context = {
               'grad_form': grad_form,
               'supervisors_form': supervisors_form,
               'status_form': status_form,               
               'page_title' : page_title,
               'crumb' : crumb
               }
    return render(request, 'grad/new.html', context)

############################################################
# temporary for adding new programs
@requires_role("GRAD")
def new_program(request):
    if request.method == 'POST':
        form = GradProgramForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse(programs))
    else:
        form = GradProgramForm()     

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
    programs = GradProgram.objects.all()
    
    # set frontend defaults
    page_title = 'Graduate Programs Records'
    crumb = 'Grad Programs' 
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'programs': programs               
               }
    return render(request, 'grad/programs.html', context)

# End of Temp
#############################################################
