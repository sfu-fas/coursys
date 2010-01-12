from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from coredata.models import OtherUser, Person
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from advisors_A.models import Note


@login_required
def index(request):
    target_userid = request.user.username
    memberships = OtherUser.objects.filter(person__userid=target_userid).filter(role='ADVS')
    student = Person.objects.get(userid = target_userid)
    return render_to_response("advisors_A/index.html", {'memberships': memberships, 'student':student}, context_instance=RequestContext(request))

@login_required
def search(request):
    if request.is_ajax():
	q = request.GET.get('q')
	results = None
	if q is not None:
	    results = Person.objects.filter(
		Q(emplid__contains = q) |
		Q(userid__contains = q) |
		Q(first_name__contains = q) |
		Q(last_name__contains = q) |
		Q(middle_name__contains = q) |
		Q(pref_first_name__contains = q)).order_by('last_name')
	#print results
	return render_to_response("advisors_A/results.html", {'results':results}, context_instance=RequestContext(request))
    else:
	return HttpResponse('<h1>Page not found</h1>')


from django.core.files import File
def handle_uploaded_file(f):
    desf = File(open(f.name, 'wb+'))    
    for chunk in f.chunks():
        desf.write(chunk)
    desf.close()


from models import *
from datetime import datetime

@login_required
def add_note(request, empId):
    """
    Add a new note
    """   
    if request.method =='POST':
        # create the form that binds to the data in the request 
        form = NoteForm(request.POST, request.FILES)
        if form.is_valid()== True:
            print request.FILES['file_uploaded'].name
            handle_uploaded_file(request.FILES['file_uploaded'])
            # save this new note            
            new_note = form.save()
            new_note.time_created = datetime.now()            
            new_note.save()      
            # return to the index page ?
            return HttpResponseRedirect(reverse('advisors_A.views.index'))     
    else:    
        # unbound
        form = NoteForm()
	target_student = Person.objects.get(emplid = empId)
	print target_student
	# we should restrict 'student' field and 'advisor' field when the form is presented

    return render_to_response("advisors_A/add_note.html", {"form" : form,}, context_instance=RequestContext(request))


@login_required
def display_notes(request, empId):
    target_student = Person.objects.get(emplid = empId )
    results = Note.objects.filter(student=target_student).order_by('-time_created')
    #print results
    
    #student's view:
    if target_student.userid == request.user.username:
	return render_to_response('advisors_A/notes_student.html', {'results':results, 'student':target_student, 'membership':False}, context_instance=RequestContext(request))
    else:
    #advisor's view
	return render_to_response("advisors_A/notes.html", { 'results':results, 'student':target_student, 'membership':True }, context_instance=RequestContext(request))