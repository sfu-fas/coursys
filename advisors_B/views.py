# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import Context, loader
from advisors_B.models import *
#from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from coredata.models import Member

def index(request):
    userid = request.user.username
    memberships = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=userid)
    return render_to_response("advisors_B/index.html", {'memberships': memberships}, context_instance=RequestContext(request))


def search(request):
    return render_to_response("advisors_B/search.html")
                              
def add_note(request):
    return render_to_response("advisors_B/add.html")

def display_note(request):
    return render_to_response("advisors_B/display.html")
