from advisornotes.forms import AdvisorNoteForm, StudentSearchForm, \
    NoteSearchForm, NonStudentForm, MergeStudentForm, ArtifactNoteForm
from advisornotes.models import AdvisorNote, NonStudent
from coredata.models import Person
from coredata.queries import find_person, add_person, more_personal_info, \
    SIMSProblem
from courselib.auth import requires_role, HttpResponseRedirect, \
    ForbiddenResponse
from courselib.search import find_userid_or_emplid, get_query
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404
from django.shortcuts import render, get_object_or_404
from log.models import LogEntry
import json
import rest
from django.views.decorators.csrf import csrf_exempt


def _redirect_to_notes(student):
    """
    Not all students have an active computing account: use userid if we can, or emplid if not.
    """
    if type(student) is Person:
        if student.userid:
            return HttpResponseRedirect(reverse('advisornotes.views.student_notes', kwargs={'userid': student.userid}))
        else:
            return HttpResponseRedirect(reverse('advisornotes.views.student_notes', kwargs={'userid': student.emplid}))
    else:
        return HttpResponseRedirect(reverse('advisornotes.views.student_notes', kwargs={'nonstudent_slug': student.slug}))


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
    note_form = NoteSearchForm()
    context = {'form': form, 'note_form': note_form}
    return render(request, 'advisornotes/student_search.html', context)


@requires_role('ADVS')
def note_search(request):
    if 'search' not in request.GET:
        return ForbiddenResponse, "must send search query"
    search = request.GET['search']
    query = get_query(search, ('text',))
    notes = AdvisorNote.objects.filter(query, unit__in=request.units) \
            .select_related('student', 'advisor').order_by("-created_at")[:100]
    note_form = NoteSearchForm(initial={'search': search})
    context = {'notes': notes, 'note_form': note_form}
    return render(request, 'advisornotes/note_search.html', context)


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
                messages.add_message(request, messages.SUCCESS, 'Record for %s created.' % (p.name()))
                return _redirect_to_notes(p)

    return HttpResponseRedirect(reverse('advisornotes.views.advising', kwargs={}))


@requires_role('ADVS')
def new_note(request, userid):
    try:
        student = Person.objects.get(find_userid_or_emplid(userid))
    except ObjectDoesNotExist:
        student = get_object_or_404(NonStudent, slug=userid)
    unit_choices = [(u.id, unicode(u)) for u in request.units]

    if request.method == 'POST':
        form = AdvisorNoteForm(request.POST, request.FILES)
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            note = form.save(commit=False)
            if isinstance(student, Person):
                note.student = student
            else:
                note.nonstudent = student
            note.advisor = Person.objects.get(userid=request.user.username)

            if 'file_attachment' in request.FILES:
                upfile = request.FILES['file_attachment']
                note.file_mediatype = upfile.content_type
                messages.add_message(request, messages.SUCCESS, 'Created file attachment "%s".' % (upfile.name))

            note.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new note for %s by %s") % (form.instance.student, request.user.username),
                  related_object=form.instance)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Note created.')
            return _redirect_to_notes(student)
    else:
        form = AdvisorNoteForm(initial={'student': student})
        form.fields['unit'].choices = unit_choices
    return render(request, 'advisornotes/new_note.html', {'form': form, 'student': student, 'userid': userid})


@requires_role('ADVS')
def new_artifact_note(request):
    unit_choices = [(u.id, unicode(u)) for u in request.units]

    if request.method == 'POST':
        form = ArtifactNoteForm(request.POST, request.FILES)
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            note = form.save(commit=False)
            note.advisor = Person.objects.get(userid=request.user.username)

            if 'file_attachment' in request.FILES:
                upfile = request.FILES['file_attachment']
                note.file_mediatype = upfile.content_type
                messages.add_message(request, messages.SUCCESS, 'Created file attachment "%s".' % (upfile.name))

            note.save()

            if note.course:
                artifact = note.course
            elif note.course_offering:
                artifact = note.course_offering
            else:
                artifact = note.artifact

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new note for %s by %s") % (artifact, request.user.username),
                  related_object=form.instance)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Note created.')
            return HttpResponseRedirect(reverse('advisornotes.views.advising', kwargs={}))
    else:
        form = ArtifactNoteForm(initial={})
        form.fields['unit'].choices = unit_choices

    return render(request, 'advisornotes/new_artifact_note.html', {'form': form})


@requires_role('ADVS')
def student_notes(request, userid):

    try:
        student = Person.objects.get(find_userid_or_emplid(userid))
    except ObjectDoesNotExist:
        student = get_object_or_404(NonStudent, slug=userid)

    if request.POST and 'note_id' in request.POST:
        # the "hide note" box was checked: process
        note = get_object_or_404(AdvisorNote, pk=request.POST['note_id'], unit__in=request.units)
        note.hidden = request.POST['hide'] == "yes"
        note.save()

    if isinstance(student, Person):
        notes = AdvisorNote.objects.filter(student=student, unit__in=request.units).order_by("-created_at")
        nonstudent = False
    else:
        notes = AdvisorNote.objects.filter(nonstudent=student, unit__in=request.units).order_by("-created_at")
        nonstudent = True

    return render(request, 'advisornotes/student_notes.html', {'notes': notes, 'student' : student, 'userid': userid, 'nonstudent': nonstudent})


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


@requires_role('ADVS')
def new_nonstudent(request):
    """
    View to create a new non-student
    """
    unit_choices = [(u.id, unicode(u)) for u in request.units]
    if request.POST:
        form = NonStudentForm(request.POST)
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            nonstudent = form.save()
            return _redirect_to_notes(nonstudent)
    else:
        form = NonStudentForm()
        form.fields['unit'].choices = unit_choices
    return render(request, 'advisornotes/new_nonstudent.html', {'form': form})


@requires_role('ADVS')
def merge_nonstudent(request, nonstudent_slug):
    """
    Merge a nonstudent with an existing student
    """
    nonstudent = get_object_or_404(NonStudent, slug=nonstudent_slug)

    if request.method == 'POST':
        form = MergeStudentForm(request.POST)
        if form.is_valid():
            student = form.cleaned_data['student']
            notes = AdvisorNote.objects.filter(nonstudent=nonstudent)
            for note in notes:
                note.nonstudent = None
                note.student = student
                note.save()
            if nonstudent.high_school:
                student.set_nonstudent_hs(nonstudent.high_school)
            if nonstudent.notes:
                student.set_nonstudent_notes(nonstudent.notes)
            nonstudent.delete()
            student.save()
            l = LogEntry(userid=request.user.username,
                  description=("Nonstudent (%s, %s) has been merged with emplid #%s by %s") % (nonstudent.last_name, nonstudent.first_name, student.emplid, request.user),
                  related_object=student)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Advisor notes successfully merged.')
            return _redirect_to_notes(student)
    else:
        form = MergeStudentForm()
    return render(request, 'advisornotes/merge_nonstudent.html', {'form': form, 'nonstudent': nonstudent})


@csrf_exempt
def rest_notes(request):
    """
    View to create new advisor notes via RESTful POST (json)
    """
    if request.method != 'POST':
        raise Http404
    try:
        rest.new_advisor_notes(request.raw_post_data)
    except ValidationError as e:
        return HttpResponse(content=e.messages[0], status=403)
    return HttpResponse(status=200)
