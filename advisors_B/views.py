# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import Context, loader
from advisors_B.models import *
#from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from courselib.auth import requires_advisor
from django.template import RequestContext
from coredata.models import Member

@login_required
def index(request):
    is_advisor = False
    for advisor in OtherUser.objects.filter(role = 'ADVS'):
        if advisor.person.userid == request.user.username:
            is_advisor = True
            break
    if is_advisor:
        return render_to_response("advisors_B/advisor.html")
    else:
        note_list = Note.objects.filter(student__userid = request.user.username).order_by('-create_date')
        print note_list
        return render_to_response("advisors_B/student.html",{'note_list':note_list})

@requires_advisor()
def search_result(request):
    return render_to_response("advisors_B/search_result.html")

@requires_advisor()
def create(request):
    return render_to_response("advisors_B/create.html")

@login_required
def detail(request, note_id):
    try:
        n = Note.objects.get(pk = note_id)
    except Note.DoesNotExist:
        raise Http404
    return render_to_response("advisors_B/detail.html",{'note':n})
