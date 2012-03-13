from django.core.urlresolvers import reverse
from django.db.models import Q
from django.shortcuts import render_to_response, get_object_or_404, render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from advisornotes.models import AdvisorNote
from coredata.models import Member, Person, Role, Unit
from django.template import RequestContext
from courselib.auth import requires_role, ForbiddenResponse, HttpResponseRedirect
from advisornotes.forms import AdvisorNoteForm, StudentSelect, StudentField, StudentSearchForm
from django.contrib import messages
from courselib.search import get_query
from coredata.queries import find_person, add_person, more_personal_info, SIMSProblem
from log.models import LogEntry
import json

def _redirect_to_notes(student):
    """
    Not all possible students have an active computing account: use userid if we can, or emplid if not.
    """
    if student.userid:
        return HttpResponseRedirect(reverse('advisornotes.views.student_notes', kwargs={'userid': student.userid}))
    else:        
        return HttpResponseRedirect(reverse('advisornotes.views.student_notes', kwargs={'userid': student.emplid}))

def _find_userid_or_emplid(userid):
    """
    Search by userid or emplid
    """
    try:
        int(userid)
        return Q(userid=userid) | Q(emplid=userid)
    except ValueError:
        return Q(userid=userid)

@requires_role('ADVS')
def advising(request):
    if request.method == 'POST':
        # find the student if we can and redirect to info page
        form = StudentSearchForm(request.POST)
        if not form.is_valid():
            simssearch = None
            if 'search' in form.data and form.data['search'].strip().isdigit():
                simssearch = form.data['search'].strip()
            context = {'form': form, 'simssearch': simssearch}
            return render_to_response('advisornotes/student_search.html', context, context_instance=RequestContext(request))
        search = form.cleaned_data['search']
        return _redirect_to_notes(search)
    form = StudentSearchForm()
    context = {'form': form}
    return render_to_response('advisornotes/student_search.html', context, context_instance=RequestContext(request))

@requires_role('ADVS')
def sims_search(request):
    emplid = request.GET.get('emplid', None)
    data = None
    if emplid:
        try:
            emplid = int(emplid.strip())
            data = find_person(emplid)
            if isinstance(data, SIMSProblem):
                data = {'error': data}
        except ValueError:
            # not an integer, so not an emplid to search for
            data = None
    
    if not data:
        data = {'error': 'could not find person in SIMS database'}

    response = HttpResponse(mimetype='application/json')
    json.dump(data, response, indent=1)
    return response

@requires_role('ADVS')
def sims_add_person(request):
    if request.method == 'POST':
        emplid = request.POST.get('emplid', None)
        if emplid:
            p = add_person(emplid.strip())
            if isinstance(p, Person):
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                       description=("added %s (%s) from SIMS") % (p.name(), p.emplid),
                      related_object=p)
                l.save()
                messages.add_message(request, messages.SUCCESS, 'Record for %s created.' % (p.name()) )
                return _redirect_to_notes(p)
    
    return HttpResponseRedirect(reverse('advisornotes.views.advising', kwargs={}))        


@requires_role('ADVS')
def new_note(request, userid):
    student = get_object_or_404(Person, _find_userid_or_emplid(userid))
    unit_choices = [(u.id, unicode(u)) for u in request.units]

    if request.method == 'POST':
        form = AdvisorNoteForm(request.POST, request.FILES)
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            note = form.save(False)
            note.student = student
            note.advisor = Person.objects.get(userid=request.user.username)

            if 'file_attachment' in request.FILES:
                upfile = request.FILES['file_attachment']
                note.file_mediatype= upfile.content_type
                messages.add_message(request, messages.SUCCESS, 'Created file attachment "%s".' % (upfile.name))
                
            note.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new note for %s by %s") % (form.instance.student, request.user.username),
                  related_object=form.instance)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Note created.' )
            notes = AdvisorNote.objects.filter(student__userid=userid)
            return _redirect_to_notes(student)
    else:
        form = AdvisorNoteForm(initial={'student': student })
        form.fields['unit'].choices = unit_choices
    return render(request, 'advisornotes/new_note.html', {'form': form, 'student':student, 'userid': userid} )
 
#@requires_role('ADVS')
#def view_note(request, userid, note_id):
#    note = get_object_or_404(AdvisorNote, pk=note_id, unit__in=request.units)
#    student = get_object_or_404(Person, _find_userid_or_emplid(userid))
#    return render(request, 'advisornotes/view_note.html', {'note': note, 'student':student}, context_instance=RequestContext(request))

@requires_role('ADVS')
def student_notes(request, userid):
    student = get_object_or_404(Person, _find_userid_or_emplid(userid))
    if request.POST:
        if request.is_ajax():
            note = get_object_or_404(AdvisorNote, pk=request.POST['note_id'], unit__in=request.units)
            if request.POST['hide']=="yes":
                note.hidden=True
            else:
                note.hidden=False
            note.save()
            
    notes = AdvisorNote.objects.filter(student=student, unit__in=request.units).order_by("-created_at")
    return render(request, 'advisornotes/student_notes.html', {'notes': notes, 'student' : student, 'userid': userid}, context_instance=RequestContext(request))
    
@requires_role('ADVS')
def download_file(request, userid, note_id):
    note = AdvisorNote.objects.get(id=note_id, unit__in=request.units)
    note.file_attachment.open()
    resp = HttpResponse(note.file_attachment, mimetype=note.file_mediatype)
    resp['Content-Disposition'] = 'inline; filename=' + note.attachment_filename()
    return resp


@requires_role('ADVS')
def student_more_info(request, userid):
    """
    AJAX request for contact info, etc. (queries SIMS directly)
    """
    student = get_object_or_404(Person, _find_userid_or_emplid(userid))
    data = more_personal_info(student.emplid, programs=True)
    
    if isinstance(data, SIMSProblem):
        data = {'error': data}
    #elif data is None:
    #    data = {'error': 'Student not found in SIMS.'}
    
    response = HttpResponse(mimetype='application/json')
    json.dump(data, response, indent=1)
    return response

