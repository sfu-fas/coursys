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
    return render_to_response("advisors_B/index.html")


def search_result(request):
    return render_to_response("advisors_B/search_result.html")
                              
def create(request):
    return render_to_response("advisors_B/create.html")

def detail(request, note_id):
    try:
        n = Note.objects.get(pk = note_id)
    except Note.DoesNotExist:
        raise Http404
    return render_to_response("advisors_B/detail.html",{'note':n})
