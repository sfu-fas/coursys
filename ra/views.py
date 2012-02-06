from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, get_object_or_404, render
from django.http import HttpResponseRedirect, HttpResponse
from ra.models import RAAppointment, Project, Account
from ra.forms import RAForm
from coredata.models import Person, Role, Unit
from django.template import RequestContext
from django.forms import *
from courselib.auth import requires_role

@requires_role("FUND")
def index(request):
    ras = RAAppointment.objects.all()
    context = {'ras': ras }
    return render(request, 'ra/index.html', context)

@requires_role("FUND")
def new(request):

    def create_new_project(self, new_project_number, new_fund_number):
        new_project = Project(project_number=new_project_number,
                              fund_number=new_fund_number)
        new_project.save()
    
    def create_new_account(self, new_account_number, new_position_number):
        new_account = Account(account_number=new_account_number,
                              position_number=new_position_number)
        new_account.save()
    
    raform = RAForm(request.POST or None)
    if request.method == 'POST':
        if raform.is_valid():
            raform.save()
            return HttpResponseRedirect(reverse(index))
    return render(request, 'ra/new.html', { 'raform': raform })