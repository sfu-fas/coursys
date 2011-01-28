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

#@requires_advisor
@login_required()
def index(request):
        username = request.user.username
        advisor = get_object_or_404(Person, userid = username)
   	return render_to_response("advisors/search_form.html",{'advisor':advisor},context_instance=RequestContext(request))

@login_required()
def search(request):
    
    query = request.GET.get('input')
    if query == None:
 	return HttpResponse(query)  
    else:
	return HttpResponse('hello world')
#    else:
#      result = Person.objects.filter(Q(emplid=query)|Q(first_name=query)|Q(last_name=query)|Q(middle_name=query))
    
#    if result == None:
#      return HttpResponse('<h1>No result founded</h1>')  
#    else:
#    render_to_resonse('view.html',{result:"result"},context_instance=RequestContext(request))
#	return HttpResponse('Hello World')
# --------------View and Add Notes------------------------

#Add Notes, only advisor can do it
#@requires_advisor
#def add_notes(request, student_NO):
#	try:
#		std = Person.objects.get(emplid = student_NO)
#	except Person.DoesNotExist:
#		raise Http404
#	try:
#		adv = Person.objects.get(userid = request.user.username)
#	except Person.DoesNotExist:
#		raise Http404
#
#	notes_content = request.POST['Detail_Text']
#
#	added_notes = Note(advisor = adv, student = std, notes = notes_content, created_date = datetime.now())
#	added_notes.save();

#	return render_to_response("advisors/Detail.html", {'note':notes_content})


#View Notes, students can read the notes of themselves, advisors can read all the notes for the choosen student
#@login_required
#def view_notes(request, student_NO):
#	try:
#		std = Person.objects.get(emplid = student_NO)
#	except Person.DoesNotExist:
#		raise Http404
#   	results = Notes.objects.filter(student=std).order_by('created_date')

#	try:
#		list_of_notes = Note.objects.get(...)
#	except Note.DoesNotExist:
#		raise Http404

#	return render_to_response("advisors/Detail.html", {'note':list_of_notes})

# --------------------------------------------------------

