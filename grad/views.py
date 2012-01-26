from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from grad.models import *
from coredata.models import Person, Role, Unit
from django.template import RequestContext
from django.forms import *
from courselib.auth import requires_advisor


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
def manage(request, user_id):
    grad = get_object_or_404(GradStudent, slug=user_id)

    context = {'grad': grad
               }
    return render(request, 'grad/manage.html', context)

@requires_advisor
def new(request):

    
    if request.method == 'POST':
        form = GradStudentForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse(index))
    else:
        form = GradStudentForm()      

    # set frontend defaults
    page_title = 'New Gradate Student Record'  
    crumb = 'New Grad' 
    context = {
               'form': form, 
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