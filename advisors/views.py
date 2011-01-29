# Create your views here.
from advisors.models import *
from courselib.auth import requires_advisor
from django.db.models import Q
from coredata.models import Person, Member, Role
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.http import HttpResponse
# --------------Searech-----------------------------------
from django.template import RequestContext

@requires_advisor
#@login_required()
def index(request):
        username = request.user.username
        advisor = get_object_or_404(Person, userid = username)
   	return render_to_response("advisors/search_form.html",{'advisor':advisor},context_instance=RequestContext(request))

@requires_advisor
#@login_required()
def search(request):
    if 'index_text' in request.GET and request.GET['index_text']:
       query = request.GET['index_text']
       result = Person.objects.filter(Q(emplid__icontains=query)|Q(first_name__icontains=query)|Q(last_name__icontains=query)|Q(middle_name__icontains=query))   
       if result:
          return render_to_response('advisors/view.html',{'results':result},context_instance=RequestContext(request))
          return HttpResponse(result)  
       else:
          return HttpResponse('<h1>No result founded</h1>')  
    else:
       return HttpResponse('input error') 
