from django.core.urlresolvers import reverse
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from advisornotes.models import AdvisorNote
from coredata.models import Person
from django.template import RequestContext
from courselib.auth import requires_role, HttpResponseRedirect
from advisornotes.forms import AdvisorNoteForm, StudentSearchForm
from django.contrib import messages
from courselib.search import find_userid_or_emplid
from coredata.queries import find_person, add_person, more_personal_info, SIMSProblem
from log.models import LogEntry
import json

def _redirect_to_notes(student):
    """
    Not all students have an active computing account: use userid if we can, or emplid if not.
    """
    if student.userid:
        return HttpResponseRedirect(reverse('advisornotes.views.student_notes', kwargs={'userid': student.userid}))
    else:        
        return HttpResponseRedirect(reverse('advisornotes.views.student_notes', kwargs={'userid': student.emplid}))

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
            return render(request, 'advisornotes/student_search.html', context)
        search = form.cleaned_data['search']
        return _redirect_to_notes(search)
    form = StudentSearchForm()
    context = {'form': form}
    return render(request, 'advisornotes/student_search.html', context)

@requires_role('ADVS')
def sims_search(request):
    emplid = request.GET.get('emplid', None)
    data = None
    if emplid:
        try:
            emplid = int(emplid.strip())
            try:
                data = find_person(emplid)
            except SIMSProblem as e:
                data = {'error': e.message}
        except ValueError:
            # not an integer, so not an emplid to search for
            data = None
    
    if not data:
        data = {'error': 'could not find person in SIMS database'}

    response = HttpResponse(mimetype='application/json')
    json.dump(data, response)
    return response

@requires_role('ADVS')
def sims_add_person(request):
    if request.method == 'POST':
        emplid = request.POST.get('emplid', None)
        if emplid:
            try:
                p = add_person(emplid.strip())
            except SIMSProblem:
                p = None

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
    student = get_object_or_404(Person, find_userid_or_emplid(userid))
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
            return _redirect_to_notes(student)
    else:
        form = AdvisorNoteForm(initial={'student': student })
        form.fields['unit'].choices = unit_choices
    return render(request, 'advisornotes/new_note.html', {'form': form, 'student':student, 'userid': userid} )

@requires_role('ADVS')
def student_notes(request, userid):
    student = get_object_or_404(Person, find_userid_or_emplid(userid))
    if request.POST and 'note_id' in request.POST:
        # the "hide note" box was checked: process
        note = get_object_or_404(AdvisorNote, pk=request.POST['note_id'], unit__in=request.units)
        note.hidden = request.POST['hide']=="yes"
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
    student = get_object_or_404(Person, find_userid_or_emplid(userid))
    try:
        data = more_personal_info(student.emplid)
    except SIMSProblem as e:
        data = {'error': e.message}
    
    response = HttpResponse(mimetype='application/json')
    json.dump(data, response)
    return response

