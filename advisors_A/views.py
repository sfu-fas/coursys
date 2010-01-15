from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from coredata.models import OtherUser, Person, Member
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from advisors_A.models import *
from courselib.auth import requires_advisor

@login_required
def index(request):
    target_userid = request.user.username
    memberships = OtherUser.objects.filter(person__userid=target_userid).filter(role='ADVS')
    student = Person.objects.get(userid = target_userid)
    return render_to_response("advisors_A/index.html", {'memberships': memberships, 'student':student}, context_instance=RequestContext(request))

@requires_advisor()
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


from datetime import datetime
@requires_advisor()
def add_note(request, empId):
    """
    Add a new note
    """   
    if request.method =='POST':
        # set the known fields of the note to be created                
        current_advisor = Person.objects.get(userid = request.user.username)   
        target_student = Person.objects.get(emplid = empId)
        default_note = Note(student = target_student, advisor = current_advisor,time_created = datetime.now())                              
       
        # create the form that binds to the data in the request   
        form = NoteForm(request.POST, request.FILES, instance = default_note)
        if form.is_valid()==True:            
            new_note = form.save()  
            new_note.save()
            # return back to the student notes page
            return HttpResponseRedirect(reverse('advisors_A.views.display_notes', args=(empId,)))             
    else:    
        # unbound     
        form = NoteForm()   
        
    return render_to_response("advisors_A/add_note.html", {"form" : form, "empid" : empId}, context_instance=RequestContext(request))


@login_required
def display_notes(request, empId):
    target_student = Person.objects.get(emplid = empId )
    results = Note.objects.filter(student=target_student).order_by('-time_created')
    memberships = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=target_student.userid) \
            .select_related('offering','person','offering__semester')
    #print memberships

    #student's view:
    if target_student.userid == request.user.username:      
        return render_to_response('advisors_A/notes_student.html', {'results':results, 'student':target_student, 'membership':False, 'course_memberships':memberships}, context_instance=RequestContext(request))
    elif OtherUser.objects.filter(person__userid=request.user.username).filter(role="ADVS"):
    #advisor's view
        return render_to_response("advisors_A/notes.html", { 'results':results, 'student':target_student, 'membership':True, 'course_memberships':memberships }, context_instance=RequestContext(request))
    else:
    #forbidden
	return render_to_response("403.html", context_instance=RequestContext(request))
