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
       return render_to_response('advisors/view.html',{'results':result},context_instance=RequestContext(request)) 
    else:
       return HttpResponse('input error')

# --------------View and Add Notes------------------------

#Add Notes, only advisor can do it
#@requires_advisor
#def add_notes(request, student_NO):
#        try:
#                std = Person.objects.get(emplid = student_NO)
#        except Person.DoesNotExist:
#                raise Http404
#        try:
#                adv = Person.objects.get(userid = request.user.username)
#        except Person.DoesNotExist:
#                raise Http404
#
#        notes_content = request.POST['Detail_Text']
#
#        added_notes = Note(advisor = adv, student = std, notes = notes_content, created_date = datetime.now())
#        added_notes.save();

#        return render_to_response("advisors/Detail.html", {'note':notes_content})


#View Notes, students can read the notes of themselves, advisors can read all the notes for the choosen student
#@login_required
def view_notes(request):
	 #query = request.GET['index_text']

#        try:
#                std = Person.objects.get(emplid = student_NO)
#        except Person.DoesNotExist:
#                raise Http404
#           results = Notes.objects.filter(student=std).order_by('created_date')

#        try:
#                list_of_notes = Note.objects.get(...)
#        except Note.DoesNotExist:
#                raise Http404
	return HttpResponse('fff')
#        return render_to_response("advisors/Detail.html", {'note':list_of_notes})

# --------------------------------------------------------
 
