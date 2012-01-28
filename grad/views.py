from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from grad.models import *
from coredata.models import Person, Role, Unit
from django.template import RequestContext
from django.forms import *
from courselib.auth import requires_advisor
from django.core import serializers
from django.utils.safestring import mark_safe


@requires_advisor
def index(request):
    grads = GradStudent.objects.all()
    
    # set frontend defaults
    page_title = 'Gradate Student Records'  
    crumb = 'Grads' 
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'grads': grads               
               }
    return render(request, 'grad/index.html', context)


@requires_advisor
def manage(request, userid):
    grad = get_object_or_404(GradStudent, slug=userid)
    supervisors = get_object_or_404(Supervisor, student=grad.id)
    
    if request.method == 'POST':
        grad_form = GradStudentForm(request.POST, instance=grad, prefix="grad")
        supervisors_form = SupervisorForm(request.POST, instance=supervisors, prefix="sup")
        if grad_form.is_valid() and supervisors_form.is_valid():
            print "All val passed"
            gradF = grad_form.save()
            supervisors_form.cleaned_data["student"] = gradF
            supervisors_form.save()
            return HttpResponseRedirect(reverse(index))
    else:
        grad_form = GradStudentForm(instance=grad, prefix="grad")
        supervisors_form = SupervisorForm(instance=supervisors, prefix="sup") 

    # set frontend defaults
    page_title = "%s 's Gradate Student Record" % (grad.person.first_name)  
    crumb = "%s %s" % (grad.person.first_name, grad.person.last_name)
    gp = grad.person.get_fields 
    supervisors = supervisors.get_fields 
    context = {'grad_form': grad_form,
               'supervisors_form': supervisors_form,
               'page_title' : page_title,
               'crumb' : crumb,
               'grad' : grad,
               'gp' : gp,
               'supervisors' : supervisors            
               }
    return render(request, 'grad/manage.html', context)

@requires_advisor
def new(request):
    if request.method == 'POST':
        grad_form = GradStudentForm(request.POST, prefix="grad")
        supervisors_form = SupervisorForm(request.POST, prefix="sup")
        if grad_form.is_valid() and supervisors_form.is_valid():
            print "All val passed"
            gradF = grad_form.save()
            sf = supervisors_form.save(commit=False)
            supervisors_form.cleaned_data["student"] = gradF
            sf.student_id = gradF.id
            supervisors_form.save()
            return HttpResponseRedirect(reverse(index))
    else:
        grad_form = GradStudentForm(prefix="grad")
        supervisors_form = SupervisorForm(prefix="sup")    

    # set frontend defaults
    page_title = 'New Gradate Student Record'  
    crumb = 'New Grad' 
    context = {
               'grad_form': grad_form,
               'supervisors_form': supervisors_form,
               'page_title' : page_title,
               'crumb' : crumb
               }
    return render(request, 'grad/new.html', context)

############################################################
# temporary for adding new programs
@requires_advisor
def new_program(request):
    if request.method == 'POST':
        form = GradProgramForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse(index))
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
@requires_advisor
def programs(request):
    programs = GradProgram.objects.all()
    
    # set frontend defaults
    page_title = 'Gradate Programs Records'  
    crumb = 'Grad Programs' 
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'programs': programs               
               }
    return render(request, 'grad/programs.html', context)

# End of Temp
#############################################################
