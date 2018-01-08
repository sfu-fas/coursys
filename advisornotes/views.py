from advisornotes.forms import StudentSearchForm, NoteSearchForm, NonStudentForm, \
    MergeStudentForm, ArtifactNoteForm, ArtifactForm, advisor_note_factory,\
    EditArtifactNoteForm, CourseSearchForm, OfferingSearchForm
from advisornotes.models import AdvisorNote, NonStudent, Artifact, ArtifactNote, AdvisorVisit
from coredata.models import Person, Course, CourseOffering, Semester, Unit, Member, Role
from coredata.queries import find_person, add_person, more_personal_info, more_course_info, course_data, transfer_data,\
    SIMSProblem, classes_data
from courselib.auth import requires_role, HttpResponseRedirect, \
    ForbiddenResponse
from courselib.search import find_userid_or_emplid, get_query
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.mail.message import EmailMessage
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.text import wrap
from django.views.decorators.http import require_POST
from log.models import LogEntry
from onlineforms.models import FormSubmission
import datetime
import json
from . import rest
from timeit import itertools
import unicodecsv as csv



def _redirect_to_notes(student):
    """
    Not all students have an active computing account: use userid if we can, or emplid if not.
    """
    if type(student) is Person:
        if student.userid:
            return HttpResponseRedirect(reverse('advising:student_notes', kwargs={'userid': student.userid}))
        else:
            return HttpResponseRedirect(reverse('advising:student_notes', kwargs={'userid': student.emplid}))
    else:
        return HttpResponseRedirect(reverse('advising:student_notes', kwargs={'nonstudent_slug': student.slug}))


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
                data = {'error': str(e)}
        except ValueError:
            # not an integer, so not an emplid to search for
            data = None

    if not data:
        data = {'error': 'could not find person in SIMS database'}

    response = HttpResponse(content_type='application/json')
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

    return HttpResponseRedirect(reverse('advising:advising', kwargs={}))


def _email_student_note(note):
    """
    Email advising note to student.
    """
    subject = "SFU Advising Note"
    from_email = note.advisor.email()
    if note.student is not None:
        email = note.student.email()
    else:
        email = note.nonstudent.email()
    content = wrap(note.text, 72)
    attach = []
    if note.file_attachment:
        note.file_attachment.open()
        attach = [(note.attachment_filename(), note.file_attachment.read(), note.file_mediatype)]

    mail = EmailMessage(subject, content, from_email, [email], cc=[from_email], attachments=attach)
    mail.send()


@requires_role('ADVS')
@transaction.atomic
def new_note(request, userid):
    try:
        student = Person.objects.get(find_userid_or_emplid(userid))
    except Person.DoesNotExist:
        student = get_object_or_404(NonStudent, slug=userid)
    unit_choices = [(u.id, str(u)) for u in request.units]

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

            if form.cleaned_data['email_student']:
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
@transaction.atomic
def new_artifact_note(request, unit_course_slug=None, course_slug=None, artifact_slug=None):
    unit_choices = [(u.id, str(u)) for u in request.units]
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
                return HttpResponseRedirect(reverse('advising:view_course_notes', kwargs={'unit_course_slug': course.slug}))
            elif offering:
                return HttpResponseRedirect(reverse('advising:view_offering_notes', kwargs={'course_slug': offering.slug}))
            else:
                return HttpResponseRedirect(reverse('advising:view_artifact_notes', kwargs={'artifact_slug': artifact.slug}))
    else:
        form = ArtifactNoteForm(initial={})
        form.fields['unit'].choices = unit_choices

    return render(request, 'advisornotes/new_artifact_note.html',
        {'form': form, 'related': related, 'artifact': artifact, 'course': course, 'offering': offering})


@requires_role('ADVS')
@transaction.atomic
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
                return HttpResponseRedirect(reverse('advising:view_course_notes', kwargs={'unit_course_slug': course.slug}))
            elif offering:
                return HttpResponseRedirect(reverse('advising:view_offering_notes', kwargs={'course_slug': offering.slug}))
            else:
                return HttpResponseRedirect(reverse('advising:view_artifact_notes', kwargs={'artifact_slug': artifact.slug}))

    return render(request, 'advisornotes/edit_artifact_note.html',
        {'form': form, 'note': note, 'related': related, 'artifact': artifact, 'course': course, 'offering': offering})


@requires_role('ADVS')
def student_notes(request, userid):

    try:
        student = Person.objects.get(find_userid_or_emplid(userid))
    except Person.DoesNotExist:
        student = get_object_or_404(NonStudent, slug=userid)

    if request.POST and 'note_id' in request.POST:
        # the "hide note" box was checked: process
        note = get_object_or_404(AdvisorNote, pk=request.POST['note_id'], unit__in=request.units)
        note.hidden = request.POST['hide'] == "yes"
        note.save()

    if isinstance(student, Person):
        notes = AdvisorNote.objects.filter(student=student, unit__in=request.units).order_by("-created_at")
        form_subs = FormSubmission.objects.filter(initiator__sfuFormFiller=student, form__unit__in=Unit.sub_units(request.units),
                                                  form__advisor_visible=True)

        # decorate with .entry_type (and .created_at if not present so we can sort nicely)
        for n in notes:
            n.entry_type = 'NOTE'
        for fs in form_subs:
            fs.entry_type = 'FORM'
            fs.created_at = fs.last_sheet_completion()

        items = list(itertools.chain(notes, form_subs))
        items.sort(key=lambda x: x.created_at, reverse=True)
        nonstudent = False
    else:
        notes = AdvisorNote.objects.filter(nonstudent=student, unit__in=request.units).order_by("-created_at")
        for n in notes:
            n.entry_type = 'NOTE'
        items = notes
        nonstudent = True
    
    show_transcript = False
    # For demo purposes only.
    # if 'UNIV' in [u.label for u in request.units]:
    #    show_transcript = True

    template = 'advisornotes/student_notes.html'
    if 'compact' in request.GET:
        template = 'advisornotes/student_notes_compact.html'
    context = {'items': items, 'student': student, 'userid': userid, 'nonstudent': nonstudent,
               'show_transcript': show_transcript, 'units': request.units}
    return render(request, template, context)


@requires_role('ADVS')
def download_file(request, userid, note_id):
    note = AdvisorNote.objects.get(id=note_id, unit__in=request.units)
    note.file_attachment.open()
    resp = HttpResponse(note.file_attachment, content_type=note.file_mediatype)
    resp['Content-Disposition'] = 'inline; filename="' + note.attachment_filename() + '"'
    return resp


@requires_role('ADVS')
def download_artifact_file(request, note_id):
    note = ArtifactNote.objects.get(id=note_id, unit__in=request.units)
    note.file_attachment.open()
    resp = HttpResponse(note.file_attachment, content_type=note.file_mediatype)
    resp['Content-Disposition'] = 'inline; filename="' + note.attachment_filename() + '"'
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
        data = {'error': str(e)}

    response = HttpResponse(content_type='application/json')
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
        data = {'error': str(e)}

    #data = {'error': 'Feature temporarily disabled.'} # disable while privacy concerns are worked out
    response = HttpResponse(content_type='application/json;charset=utf-8')
    json.dump(data, response, encoding='utf-8', indent=1)
    return response


@requires_role('ADVS')
def student_courses_download(request, userid):
    student = get_object_or_404(Person, find_userid_or_emplid(userid))
    try:
        data = classes_data(student.emplid)
    except SIMSProblem as e:
        data = {'error': str(e)}

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'inline; filename="%s-%s-courses.csv"' % (userid,
                                                                        datetime.datetime.now().strftime('%Y%m%d'))
    writer = csv.writer(response)

    writer.writerow(['Employee ID', 'Last Name', 'First Name'])
    writer.writerow([student.emplid, student.last_name, student.first_name])
    writer.writerow([])

    writer.writerow(['Semester', 'Subject', 'Catalogue Number', 'Description', 'Official Grade', 'Units Taken'])
    if 'courses' in data:
        for crse in data['courses']:
            strm = crse.get('strm') or ''
            descr = crse.get('descr') or ''
            subject = crse.get('subject') or ''
            catalog_nbr = crse.get('catalog_nbr') or ''
            crse_grade_off = crse.get('crse_grade_off') or ''
            unt_taken = crse.get('unt_taken') or 0

            writer.writerow([strm, subject, catalog_nbr, descr, crse_grade_off, unt_taken])

    return response

@requires_role('ADVS')
def student_transfers_data(request, userid):
    """
    AJAX request for transfer data, etc. (queries SIMS directly)
    """
    student = get_object_or_404(Person, find_userid_or_emplid(userid))
    try:
        data = transfer_data(student.emplid)
    except SIMSProblem as e:
        data = {'error': str(e)}

    response = HttpResponse(content_type='application/json;charset=utf-8')
    json.dump(data, response, encoding='utf-8', indent=1)
    return response


@requires_role('ADVS')
def student_transfers(request, userid):
    """
    List of transfer credits for a given student
    """
    student = get_object_or_404(Person, find_userid_or_emplid(userid))

    context = {
               'userid': userid,
               'student': student,
               }
    return render(request, 'advisornotes/student_transfers.html', context)


@requires_role('ADVS')
def student_transfers_download(request, userid):
    student = get_object_or_404(Person, find_userid_or_emplid(userid))
    try:
        data = transfer_data(student.emplid)
    except SIMSProblem as e:
        data = {'error': str(e)}

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'inline; filename="%s-%s-transfers.csv"' % (userid,
                                                                        datetime.datetime.now().strftime('%Y%m%d'))
    writer = csv.writer(response)

    writer.writerow(['Employee ID', 'Last Name', 'First Name'])
    writer.writerow([student.emplid, student.last_name, student.first_name])
    writer.writerow([])

    writer.writerow(['Description', 'School Subject', 'Course Number', 'Transfer Equivalency Group', 'Transfer Status',
                     'Subject', 'Catalogue Number', 'Transfer Grade Input', 'Transfer Official Grade',
                     'External Grade Input', 'External Official Grade', 'Units Transferred'])
    if 'transfers' in data:
        for trns in data['transfers']:
            descr = trns.get('descr') or ''
            school_subject = trns.get('school_subject') or ''
            crse_nbr = trns.get('crse_nbr') or ''
            trsnf_equivlncy_grp = trns.get('trsnf_equivlncy_grp') or ''
            transfr_stat = trns.get('transfr_stat') or ''
            subject = trns.get('subject') or ''
            catalog_nbr = trns.get('catalog_nbr') or ''
            tcd_grade_input = trns.get('tcd_grade_input') or ''
            tcd_grade_off = trns.get('tcd_grade_off') or ''
            ec_grade_input = trns.get('ec_grade_input') or ''
            ec_grade_off = trns.get('ec_grade_off') or ''
            unt_trnsfr = trns.get('unt_trnsfr') or 0

            writer.writerow([descr, school_subject, crse_nbr, trsnf_equivlncy_grp, transfr_stat, subject, catalog_nbr,
                             tcd_grade_input, tcd_grade_off, ec_grade_input, ec_grade_off, unt_trnsfr])

    return response


@requires_role('ADVS')
@require_POST
def record_advisor_visit(request, userid, unit_slug):
    unit = get_object_or_404(Unit, slug=unit_slug, id__in=(u.id for u in request.units))
    advisor = get_object_or_404(Person, userid=request.user.username)
    try:
        student = Person.objects.get(find_userid_or_emplid(userid))
        nonstudent = None
    except Person.DoesNotExist:
        nonstudent = get_object_or_404(NonStudent, slug=userid)
        student = None

    av = AdvisorVisit(student=student, nonstudent=nonstudent, program=None, advisor=advisor, unit=unit)
    av.save()

    messages.add_message(request, messages.SUCCESS, '%s advisor visit recorded on %s.' % (unit.informal_name(), datetime.date.today()))
    return HttpResponseRedirect(reverse('advising:student_notes', kwargs={'userid': userid}))


@requires_role('ADVS')
def all_visits(request):
    visits = AdvisorVisit.objects.filter(unit__in=request.units).select_related('student', 'nonstudent', 'advisor')
    context = {'visits': visits}
    return render(request, 'advisornotes/all_visits.html', context)


@requires_role('ADVS')
@transaction.atomic
def new_nonstudent(request):
    """
    View to create a new non-student
    """
    unit_choices = [(u.id, str(u)) for u in request.units]
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
@transaction.atomic
def new_artifact(request):
    """
    View to create a new artifact
    """
    unit_choices = [(u.id, str(u)) for u in request.units]
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
            return HttpResponseRedirect(reverse('advising:view_artifacts', kwargs={}))
    else:
        form = ArtifactForm()
        form.fields['unit'].choices = unit_choices
    return render(request, 'advisornotes/new_artifact.html', {'form': form})


@requires_role('ADVS')
@transaction.atomic
def edit_artifact(request, artifact_slug):
    """
    View to edit a new artifact
    """
    artifact = get_object_or_404(Artifact, slug=artifact_slug)
    unit_choices = [(u.id, str(u)) for u in request.units]
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
            return HttpResponseRedirect(reverse('advising:view_artifacts', kwargs={}))
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
    artifact = get_object_or_404(Artifact, slug=artifact_slug, unit__in=request.units)
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
    if 'coursesearch' in request.GET and 'course' in request.GET \
            and request.GET['course'] and request.GET['course'].isdigit():
        # handle the search for other courses
        offering = get_object_or_404(Course, id=request.GET['course'])
        return HttpResponseRedirect(reverse('advising:view_course_notes', kwargs={'unit_course_slug': offering.slug}))

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
    form = CourseSearchForm()

    return render(request,
        'advisornotes/view_courses.html',
        {'courses': courses, 'with_note_ids': with_note_ids, 'form': form}
    )


@requires_role('ADVS')
def view_course_notes(request, unit_course_slug):
    """
    View to view all notes for a specific artifact
    """
    course = get_object_or_404(Course, slug=unit_course_slug)
    offerings = CourseOffering.objects.filter(course=course)
    notes = ArtifactNote.objects.filter(course=course, unit__in=request.units).order_by('-created_at')
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
        data = {'error': str(e)}

    response = HttpResponse(content_type='application/json')
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
    
    if 'offeringsearch' in request.GET and request.GET['offeringsearch'] and request.GET['offeringsearch'].isdigit():
        # handle the search for other offerings
        offering = get_object_or_404(CourseOffering, id=request.GET['offering'])
        return HttpResponseRedirect(reverse('advising:view_offering_notes', kwargs={'course_slug': offering.slug}))

    subunits = Unit.sub_unit_ids(request.units)
    offerings = CourseOffering.objects.filter(owner__in=subunits, semester=semester)
    form = OfferingSearchForm()
    return render(request,
        'advisornotes/view_course_offerings.html',
        {'offerings': offerings, 'semester': semester, 'semesters': semesters, 'form': form}
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
@transaction.atomic
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
@transaction.atomic
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
            # If we had an email address for this nonstudent, store it in the application email address, like
            # for a grad student.  We really don't have a better place to store this.  The other option would be
            # to drop it altogether.
            if nonstudent.email_address:
                student.config['applic_email'] = nonstudent.email_address
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


#@csrf_exempt
#@transaction.commit_manually
def xxx_rest_notes(request):
    """
    View to create new advisor notes via RESTful POST (json)
    """

    if request.method != 'POST':
        resp = HttpResponse(content='Only POST requests allowed', status=405)
        resp['Allow'] = 'POST'
        transaction.rollback()
        return resp

    if request.META['CONTENT_TYPE'] != 'application/json' and not request.META['CONTENT_TYPE'].startswith('application/json;'):
        transaction.rollback()
        return HttpResponse(content='Contents must be JSON (application/json)', status=415)

    try:
        rest.new_advisor_notes(request.body)
    except UnicodeDecodeError:
        transaction.rollback()
        return HttpResponse(content='Bad UTF-8 encoded text', status=400)
    except ValueError:
        transaction.rollback()
        return HttpResponse(content='Bad JSON in request body', status=400)
    except ValidationError as e:
        transaction.rollback()
        return HttpResponse(content=e.messages[0], status=422)
    except Exception as e:
        transaction.rollback()
        raise

    transaction.commit()
    return HttpResponse(status=200)


