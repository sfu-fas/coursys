from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from grad.models import GradStudent, GradStudentForm
from coredata.models import Person, Role, Unit
from django.template import RequestContext
from django.forms import *
from courselib.auth import requires_advisor


@requires_advisor
def index(request):
    grads = GradStudent.objects.all()
    context = {'grads': grads               }
    return render(request, 'grad/index.html', context)
    #return HttpResponse('muu')


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
    return render(request, 'grad/new.html', {'form': form})


