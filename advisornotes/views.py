from advisornotes.forms import StudentSearchForm, NoteSearchForm, NonStudentForm, \
    MergeStudentForm, ArtifactNoteForm, ArtifactForm, advisor_note_factory,\
    ProblemStatusForm, EditArtifactNoteForm
from advisornotes.models import AdvisorNote, NonStudent, Artifact, ArtifactNote,\
    Problem, OPEN_STATUSES, CLOSED_STATUSES
from coredata.models import Person, Course, CourseOffering, Semester, Unit, Member
from coredata.queries import find_person, add_person, more_personal_info, more_course_info, course_data, \
    SIMSProblem
from courselib.auth import requires_role, HttpResponseRedirect, \
    ForbiddenResponse
from courselib.search import find_userid_or_emplid, get_query
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.mail.message import EmailMessage
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.text import wrap
from django.views.decorators.csrf import csrf_exempt
from log.models import LogEntry
import datetime
import json
import rest
from timeit import itertools
from django.db import transaction


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
    note_form = NoteSearchForm(prefix="text")
    context = {'form': form, 'note_form': note_form}
    return render(request, 'advisornotes/student_search.html', context)


@requires_role('ADVS')
def note_search(request):
    if 'text-search' not in request.GET:
        return ForbiddenResponse(request, "must send search query")
    search = request.GET['text-search']
    query = get_query(search, ('text',))
    notes = AdvisorNote.objects.filter(query, unit__in=request.units) \
            .select_related('student', 'advisor').order_by("-created_at")[:100]
    note_form = NoteSearchForm(prefix="text", initial={'search': search})
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


def _email_student_note(note):
    """
    Email advising note to student.
    """
    subject = "SFU Advising Note"
    from_email = note.advisor.email()
    email = note.student.email()
    content = wrap(note.text, 72)
    attach = []
    if note.file_attachment:
        note.file_attachment.open()
        attach = [(note.attachment_filename(), note.file_attachment.read(), note.file_mediatype)]

    mail = EmailMessage(subject, content, from_email, [email], cc=[from_email], attachments=attach)
    mail.send()


@requires_role('ADVS')
def new_note(request, userid):
    try:
        student = Person.objects.get(find_userid_or_emplid(userid))
    except ObjectDoesNotExist:
        student = get_object_or_404(NonStudent, slug=userid)
    unit_choices = [(u.id, unicode(u)) for u in request.units]

    if request.method == 'POST':
        form = advisor_note_factory(student, request.POST, request.FILES)
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

            if isinstance(student, Person) and form.cleaned_data['email_student']:
                _email_student_note(note)
                note.emailed = True

            note.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new note for %s by %s") % (form.instance.student, request.user.username),
                  related_object=form.instance)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Note created.')

            return _redirect_to_notes(student)
    else:
        form = advisor_note_factory(student)
        form.fields['unit'].choices = unit_choices
    return render(request, 'advisornotes/new_note.html', {'form': form, 'student': student, 'userid': userid})


@requires_role('ADVS')
def new_artifact_note(request, unit_course_slug=None, course_slug=None, artifact_slug=None):
    unit_choices = [(u.id, unicode(u)) for u in request.units]
    related = course = offering = artifact = None

    if unit_course_slug != None:
        related = course = get_object_or_404(Course, slug=unit_course_slug)
    elif course_slug != None:
        related = offering = get_object_or_404(CourseOffering, slug=course_slug)
    else:
        related = artifact = get_object_or_404(Artifact, slug=artifact_slug)

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

            if course:
                note.course = course
            elif offering:
                note.course_offering = offering
            else:
                note.artifact = artifact

            note.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new note for %s by %s") % (related, request.user.username),
                  related_object=form.instance)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Note for %s created.' % related)

            if course:
                return HttpResponseRedirect(reverse('advisornotes.views.view_course_notes', kwargs={'unit_course_slug': course.slug}))
            elif offering:
                return HttpResponseRedirect(reverse('advisornotes.views.view_offering_notes', kwargs={'course_slug': offering.slug}))
            else:
                return HttpResponseRedirect(reverse('advisornotes.views.view_artifact_notes', kwargs={'artifact_slug': artifact.slug}))
    else:
        form = ArtifactNoteForm(initial={})
        form.fields['unit'].choices = unit_choices

    return render(request, 'advisornotes/new_artifact_note.html',
        {'form': form, 'related': related, 'artifact': artifact, 'course': course, 'offering': offering})


@requires_role('ADVS')
def edit_artifact_note(request, note_id, unit_course_slug=None, course_slug=None, artifact_slug=None):
    note = get_object_or_404(ArtifactNote, id=note_id, unit__in=request.units)
    related = course = offering = artifact = None

    form = EditArtifactNoteForm(instance=note)

    if unit_course_slug != None:
        related = course = get_object_or_404(Course, slug=unit_course_slug)
    elif course_slug != None:
        related = offering = get_object_or_404(CourseOffering, slug=course_slug)
    else:
        related = artifact = get_object_or_404(Artifact, slug=artifact_slug)

    if request.method == 'POST':
        form = EditArtifactNoteForm(request.POST, request.FILES, instance=note)

        if form.is_valid():
            note = form.save(commit=False)
            note.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edit note for %s by %s") % (related, request.user.username),
                  related_object=form.instance)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Note for %s edited.' % related)

            if course:
                return HttpResponseRedirect(reverse('advisornotes.views.view_course_notes', kwargs={'unit_course_slug': course.slug}))
            elif offering:
                return HttpResponseRedirect(reverse('advisornotes.views.view_offering_notes', kwargs={'course_slug': offering.slug}))
            else:
                return HttpResponseRedirect(reverse('advisornotes.views.view_artifact_notes', kwargs={'artifact_slug': artifact.slug}))

    return render(request, 'advisornotes/edit_artifact_note.html',
        {'form': form, 'note': note, 'related': related, 'artifact': artifact, 'course': course, 'offering': offering})


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
        problems = Problem.objects.filter(person=student, unit__in=request.units).order_by("-created_at")
        models = list(itertools.chain(notes, problems))
        models.sort(key=lambda x: x.created_at, reverse=True)
        items = []
        for model in models:
            item = {'item': model, 'note': isinstance(model, AdvisorNote)}
            items.append(item)
        nonstudent = False
    else:
        notes = AdvisorNote.objects.filter(nonstudent=student, unit__in=request.units).order_by("-created_at")
        items = []
        for note in notes:
            item = {'item': note, 'note': True}
            items.append(item)
        nonstudent = True

    return render(request, 'advisornotes/student_notes.html', {'items': items, 'student': student, 'userid': userid, 'nonstudent': nonstudent})


@requires_role('ADVS')
def download_file(request, userid, note_id):
    note = AdvisorNote.objects.get(id=note_id, unit__in=request.units)
    note.file_attachment.open()
    resp = HttpResponse(note.file_attachment, mimetype=note.file_mediatype)
    resp['Content-Disposition'] = 'inline; filename=' + note.attachment_filename()
    return resp


@requires_role('ADVS')
def download_artifact_file(request, note_id):
    note = ArtifactNote.objects.get(id=note_id, unit__in=request.units)
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
def student_courses(request, userid):
    """
    List of courses now (and in surrounding semesters)
    """
    student = get_object_or_404(Person, find_userid_or_emplid(userid))
    
    context = {
               'userid': userid,
               'student': student,
               }
    return render(request, 'advisornotes/student_courses.html', context)

@requires_role('ADVS')
def student_courses_data(request, userid):
    """
    AJAX request for course data, etc. (queries SIMS directly)
    """
    student = get_object_or_404(Person, find_userid_or_emplid(userid))
    try:
        data = course_data(student.emplid)
    except SIMSProblem as e:
        data = {'error': e.message}

    response = HttpResponse(mimetype='application/json;charset=utf-8')
    json.dump(data, response, encoding='utf-8', indent=1)
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
def new_artifact(request):
    """
    View to create a new artifact
    """
    unit_choices = [(u.id, unicode(u)) for u in request.units]
    if request.POST:
        form = ArtifactForm(request.POST)
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            artifact = form.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new artifact %s by %s") % (artifact, request.user.username),
                  related_object=form.instance)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Artifact "%s" created.' % artifact)
            return HttpResponseRedirect(reverse('advisornotes.views.view_artifacts', kwargs={}))
    else:
        form = ArtifactForm()
        form.fields['unit'].choices = unit_choices
    return render(request, 'advisornotes/new_artifact.html', {'form': form})


@requires_role('ADVS')
def edit_artifact(request, artifact_slug):
    """
    View to edit a new artifact
    """
    artifact = get_object_or_404(Artifact, slug=artifact_slug)
    unit_choices = [(u.id, unicode(u)) for u in request.units]
    if request.POST:
        form = ArtifactForm(request.POST, instance=artifact)
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            artifact = form.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edited artifact %s by %s") % (artifact, request.user.username),
                  related_object=form.instance)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Artifact "%s" edited.' % artifact)
            return HttpResponseRedirect(reverse('advisornotes.views.view_artifacts', kwargs={}))
    else:
        form = ArtifactForm(instance=artifact)
        form.fields['unit'].choices = unit_choices
    return render(request, 'advisornotes/edit_artifact.html', {'form': form, 'artifact': artifact})


@requires_role('ADVS')
def view_artifacts(request):
    """
    View to view all artifacts
    """
    artifacts = Artifact.objects.filter(unit__in=request.units)
    return render(request,
        'advisornotes/view_artifacts.html',
        {'artifacts': artifacts}
    )


@requires_role('ADVS')
def view_artifact_notes(request, artifact_slug):
    """
    View to view all notes for a specific artifact
    """
    artifact = get_object_or_404(Artifact, slug=artifact_slug)
    notes = ArtifactNote.objects.filter(artifact__slug=artifact_slug).order_by('category', 'created_at')
    important_notes = notes.filter(important=True)
    notes = notes.exclude(important=True)
    return render(request,
        'advisornotes/view_artifact_notes.html',
        {'artifact': artifact, 'notes': notes, 'important_notes': important_notes}
    )


@requires_role('ADVS')
def view_courses(request):
    """
    View to view all courses
    """
    # all courses where a recent offering was owned by relevant units
    subunits = Unit.sub_unit_ids(request.units)
    old_sem = Semester.get_semester(datetime.date.today() - datetime.timedelta(days=365 * 2))
    offerings = CourseOffering.objects.filter(owner__in=subunits, semester__name__gte=old_sem.name) \
                                      .values('course').order_by().distinct()

    # all courses where there are notes from relevant units
    notes = ArtifactNote.objects.filter(unit__in=request.units).exclude(course__isnull=True) \
                                .values('course').order_by().distinct()
    
    with_note_ids = set(n['course'] for n in notes)
    course_ids = set(o['course'] for o in offerings)
    course_ids |= with_note_ids

    # all current CourseOfferings with notes: interested in those Courses too
    offering_notes = ArtifactNote.objects.filter(unit__in=request.units, course_offering__semester__name__gte=old_sem.name) \
                                        .values('course_offering__course').order_by().distinct()
    offering_note_ids = set(n['course_offering__course'] for n in offering_notes)
    with_note_ids |= offering_note_ids
    course_ids |= offering_note_ids
    
    courses = Course.objects.filter(id__in=course_ids)

    return render(request,
        'advisornotes/view_courses.html',
        {'courses': courses, 'with_note_ids': with_note_ids}
    )


@requires_role('ADVS')
def view_course_notes(request, unit_course_slug):
    """
    View to view all notes for a specific artifact
    """
    course = get_object_or_404(Course, slug=unit_course_slug)
    offerings = CourseOffering.objects.filter(course=course)
    notes = ArtifactNote.objects.filter(course=course, unit__in=request.units).order_by('category', 'created_at')
    important_notes = notes.filter(important=True)
    notes = notes.exclude(important=True)

    # offerings with notes
    offering_notes = ArtifactNote.objects.filter(unit__in=request.units, course_offering__course=course) \
                                        .values('course_offering').order_by().distinct()
    with_note_ids = set(n['course_offering'] for n in offering_notes)
    
    return render(request,
        'advisornotes/view_course_notes.html',
        {'course': course, 'offerings': offerings, 'notes': notes, 'important_notes': important_notes, 'with_note_ids': with_note_ids}
    )


@requires_role('ADVS')
def course_more_info(request, unit_course_slug):
    """
    AJAX request for calendar description, etc. (queries SIMS directly)
    """
    course = get_object_or_404(Course, slug=unit_course_slug)

    try:
        data = more_course_info(course)
        if not data:
            data = {'error': 'Could not find course to fetch more info.'}
    except SIMSProblem as e:
        data = {'error': e.message}

    response = HttpResponse(mimetype='application/json')
    json.dump(data, response)
    return response


@requires_role('ADVS')
def view_course_offerings(request, semester=None):
    """
    View to view all courses
    """
    if semester:
        semester = get_object_or_404(Semester, name=semester)
        semesters = None
    else:
        semester = Semester.get_semester(date=datetime.date.today() + datetime.timedelta(days=60))
        semesters = Semester.objects.filter(start__lte=datetime.date.today() + datetime.timedelta(days=365)).order_by('-end')[:6]

    subunits = Unit.sub_unit_ids(request.units)
    offerings = CourseOffering.objects.filter(owner__in=subunits, semester=semester)
    return render(request,
        'advisornotes/view_course_offerings.html',
        {'offerings': offerings, 'semester': semester, 'semesters': semesters}
    )


@requires_role('ADVS')
def view_all_semesters(request):
    """
    View to view all semesters
    """
    semesters = Semester.objects.all()
    return render(request,
        'advisornotes/view_all_semesters.html',
        {'semesters': semesters}
    )


@requires_role('ADVS')
def view_offering_notes(request, course_slug):
    """
    View to view all notes for a specific artifact
    """
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    notes = ArtifactNote.objects.filter(course_offering=offering, unit__in=request.units).order_by('category', 'created_at')
    important_notes = notes.filter(important=True)
    notes = notes.exclude(important=True)
    
    return render(request,
        'advisornotes/view_offering_notes.html',
        {'offering': offering, 'notes': notes, 'important_notes': important_notes}
    )


@requires_role('ADVS')
def hide_note(request):
    """
    View to hide a note
    """
    if request.POST and 'note_id' in request.POST:
        # the "hide note" box was checked: process
        note = get_object_or_404(ArtifactNote, pk=request.POST['note_id'], unit__in=request.units)
        note.hidden = request.POST['hide'] == "yes"
        note.save()
        return HttpResponse(status=200)
    return HttpResponse(status=403)


@requires_role('ADVS')
def merge_nonstudent(request, nonstudent_slug):
    """
    Merge a nonstudent with an existing student
    """
    nonstudent = get_object_or_404(NonStudent, slug=nonstudent_slug, unit__in=request.units)

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
            if nonstudent.college:
                student.set_nonstudent_colg(nonstudent.college)
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
@transaction.commit_manually
def rest_notes(request):
    """
    View to create new advisor notes via RESTful POST (json)
    """
    if request.method != 'POST':
        resp = HttpResponse(content='Only POST requests allowed', status=405)
        resp['Allow'] = 'POST'
        return resp

    if request.META['CONTENT_TYPE'] != 'application/json' and not request.META['CONTENT_TYPE'].startswith('application/json;'):
        return HttpResponse(content='Contents must be JSON (application/json)', status=415)

    try:
        rest.new_advisor_notes(request.raw_post_data)
    except UnicodeDecodeError:
        return HttpResponse(content='Bad UTF-8 encoded text', status=400)
    except ValueError:
        return HttpResponse(content='Bad JSON in request body', status=400)
    except ValidationError as e:
        transaction.rollback()
        return HttpResponse(content=e.messages[0], status=422)

    transaction.commit()
    return HttpResponse(status=200)


@requires_role('ADVS')
def view_problems(request):
    """
    View reported problems created via the API
    """
    problems = Problem.objects.filter(unit__in=request.units, status__in=OPEN_STATUSES)
    return render(request, 'advisornotes/view_problems.html', {'problems': problems})


@requires_role('ADVS')
def view_resolved_problems(request):
    """
    View reported problems that have been resolved
    """
    problems = Problem.objects.filter(unit__in=request.units, status__in=CLOSED_STATUSES)
    return render(request, 'advisornotes/view_resolved_problems.html', {'problems': problems})


@requires_role('ADVS')
def edit_problem(request, prob_id):
    """
    View to view and edit a problem's status
    """
    problem = get_object_or_404(Problem, pk=prob_id, unit__in=request.units)
    from_page = request.GET.get('from', '')
    if not from_page in ('resolved', ''):
        userid = from_page
        try:
            from_page = Person.objects.get(userid=userid)
        except Person.DoesNotExist:
            from_page = ''
    if request.method == 'POST':
        form = ProblemStatusForm(request.POST, instance=problem)
        if form.is_valid():
            problem = form.save(commit=False)
            if problem.is_closed():
                problem.resolved_at = datetime.datetime.now()
            else:
                problem.resolved_at = None
            problem.save()
            messages.add_message(request, messages.SUCCESS, "Problem status successfully changed.")
            return HttpResponseRedirect(reverse('advisornotes.views.view_problems'))
    else:
        if problem.is_closed():
            form = ProblemStatusForm(instance=problem)
        else:
            form = ProblemStatusForm(instance=problem, initial={'resolved_until': problem.default_resolved_until()})
    return render(request, 'advisornotes/edit_problem.html', {'problem': problem, 'from_page': from_page, 'form': form})
