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
from django.core.urlresolvers import reverse
from datetime import datetime

@login_required
def index(request):
    is_advisor = True
    for advisor in Role.objects.filter(role = 'ADVS'):
        if advisor.person.userid == request.user.username:
            is_advisor = True
            break
    if is_advisor:
        return render_to_response("advisors_B/advisor.html")
    else:
        note_list = Note.objects.filter(student__userid = request.user.username).order_by('-create_date')
        print note_list
        return render_to_response("advisors_B/student.html",{'note_list':note_list})

@login_required()
def search_result(request):
    return render_to_response("advisors_B/searchresult.html")

@login_required()
def create(request, advisor_id, student_id):
    p = Person.objects.get(userid = advisor_id)
    c_advisor = Role.objects.get(person = p)
    c_student = Person.objects.get(userid = student_id)
    new_note=Note(student=c_student,author=c_advisor,create_date = datetime.now())
    if request.method=='POST':
        form = NoteForm(request.POST,request.FILES,instance = new_note)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('advisors_B.views.search', args=({'note':new_note},)))   
    else:
            form = NoteForm()
    new_note.save()
    return render_to_response("advisors_B/create.html", {'advisor':c_advisor, 'student': c_student, 'id':new_note.id})

@login_required
def detail(request, note_id):
    try:
        n = Note.objects.get(pk = note_id)
    except Note.DoesNotExist:
        raise Http404
    return render_to_response("advisors_B/detail.html",{'note':n})
