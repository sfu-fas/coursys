from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from ra.models import RAApplication, RAForm
from coredata.models import Person, Role, Unit
from django.template import RequestContext
from django.forms import *

def index(request):
    ras = RAApplication.objects.all()
    context = {'ras': ras }
    return render(request, 'ra/index.html', context)

def manage(request, user_id):
    grad = get_object_or_404(RA)
    context = {'ra': ra }
    return render(request, 'ra/manage.html', context)

def new(request):
    if request.method == 'POST':
        form = RAForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse(index))
    else:
        form = RAForm()
    return render(request, 'ra/new.html', {'form': form})