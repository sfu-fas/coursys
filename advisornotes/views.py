from django.core.urlresolvers import reverse
from django.db.models import Q
from django.shortcuts import render_to_response, get_object_or_404, render
from django.http import HttpResponse
from advisornotes.models import AdvisorNote
from coredata.models import Member, Person, Role
from django.template import RequestContext
from courselib.auth import *
from forms import *
from django.contrib import messages

"""
@requires_advisor
def all_notes(request):
    #advisor should only see notes from his/her department
    notes = AdvisorNote.objects.all()
    dept = [r.department for r in Role.objects.filter(person__userid=request.user.username)]
    #notes = AdvisorNote.objects.filter(department=dept[0])
    return render_to_response("advisornotes/all_notes.html", {'notes': notes}, context_instance=RequestContext(request))
"""

@requires_advisor
def new_note(request):
    if request.method == 'POST':
        form = AdvisorNoteForm(request.POST)
        if form.is_valid():
            note = form.save(False)
            note.advisor_id = Person.objects.get(userid = request.user.username).id
            note.save()
            """
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new note: for %s") % (form.instance.student),
                  related_object=form.instance)
            l.save()
            """
            return HttpResponseRedirect(reverse(student_search))
    else:
        form = AdvisorNoteForm()
    return render(request, 'advisornotes/new_note.html', {'form': form})
 
@requires_advisor
def view_note(request, note_id):
    note = get_object_or_404(AdvisorNote, pk = note_id)
    student = Person.objects.get(id = note.student_id)
    return render(request, 'advisornotes/view_note.html', {'note': note, 'student' : student}, context_instance=RequestContext(request))

@requires_advisor
def student_search(request):
    if request.method == 'POST':
        # find the student if we can and redirect to info page
        form = StudentSearchForm(request.POST)
        if not form.is_valid():
            messages.add_message(request, messages.ERROR, 'Invalid search')
            context = {'form': form}
            return render_to_response('advisornotes/student_search.html', context, context_instance=RequestContext(request))

        search = form.cleaned_data['search']
        try:
            int(search)
            students = Member.objects.filter(role="STUD").filter(Q(person__userid=search) | Q(person__emplid=search))
        except ValueError:
            students = Member.objects.filter(role="STUD").filter(person__userid=search)
            #students = Person.objects.filter(member__role="STUD").filter(userid=search)
        
        if len(students)==0:
            messages.add_message(request, messages.ERROR, 'No student found')
            context = {'form': form}
            return render_to_response('advisornotes/student_search.html', context, context_instance=RequestContext(request))
        
        student = students[0]
        return HttpResponseRedirect(reverse('advisornotes.views.student_notes',
                                                kwargs={'userid': student.person.userid}))
    form = StudentSearchForm()
    context = {'form': form}
    return render_to_response('advisornotes/student_search.html', context, context_instance=RequestContext(request))

@requires_advisor
def student_notes(request,userid):
    notes = AdvisorNote.objects.filter(student__userid=userid)
    student = Person.objects.get(userid = userid)
    return render(request, 'advisornotes/student_notes.html', {'notes': notes, 'student' : student}, context_instance=RequestContext(request))
    
