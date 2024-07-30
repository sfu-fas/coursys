from advisornotes.forms import StudentSearchForm, NoteSearchForm, NonStudentForm, AnnouncementForm, \
    MergeStudentForm, ArtifactNoteForm, ArtifactForm, AdvisorNoteForm, AdvisorVisitFormInitial, \
    EditArtifactNoteForm, CourseSearchForm, OfferingSearchForm, ArtifactSearchForm, AdvisorVisitCategoryForm, \
    AdvisorVisitFormSubsequent
from advisornotes.models import AdvisorNote, Announcement, NonStudent, Artifact, ArtifactNote, AdvisorVisit, AdvisorVisitCategory, \
    ADVISOR_VISIT_VERSION
from coredata.models import Person, Course, CourseOffering, Semester, Unit, Role
from coredata.queries import find_person, add_person, more_personal_info, more_course_info, course_data, transfer_data,\
    SIMSProblem, classes_data
from courselib.auth import requires_role, HttpResponseRedirect, \
    ForbiddenResponse
from courselib.search import find_userid_or_emplid, get_query
from grades.views import has_photo_agreement
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.mail.message import EmailMultiAlternatives
from django.urls import reverse
from django.db import transaction
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST
from django.utils.html import mark_safe
from log.models import LogEntry
from onlineforms.models import FormSubmission
import datetime
import json
from . import rest
from timeit import itertools
import csv
import urllib.parse



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


@requires_role(['ADVS', 'ADVM'])
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
    artifact_form = ArtifactSearchForm(prefix="text")
    advisor_admin = Role.objects_fresh.filter(role='ADVM', person__userid=request.user.username).exists()
    entries = Announcement.objects.filter(created_at__gte=datetime.datetime.now()-datetime.timedelta(days=14), hidden=False)[:3]
    context = {'form': form, 'note_form': note_form, 'artifact_form': artifact_form, 'advisor_admin': advisor_admin, 'entries': entries}
    return render(request, 'advisornotes/student_search.html', context)


@requires_role(['ADVS','ADVM'])
def new_announcement(request: HttpRequest) -> HttpResponse:
    """
    View to create a new announcement
    """
    author = get_object_or_404(Person, userid=request.user.username)
    if request.method == 'POST':
        form = AnnouncementForm(units=request.units, data=request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.author = author
            announcement.save()
            
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'Announcement was created.'
                                 )
            l = LogEntry(userid=request.user.username,
                         description="added advising announcement: %s" % (announcement),
                         related_object=announcement
                         )
            l.save()
            return HttpResponseRedirect(reverse('advising:news'))
    else: 
        form = AnnouncementForm(units=request.units)

    return render(request, 'advisornotes/new_announcement.html', {'form': form})


@requires_role(['ADVS', 'ADVM'])
def news(request: HttpRequest) -> HttpResponse:
    """
    View to show news page
    """
    entries = Announcement.objects.filter(created_at__gte=datetime.datetime.now()-datetime.timedelta(days=180), hidden=False, unit__in=request.units)
    return render(request, 'advisornotes/news.html', {'entries': entries})

@requires_role(['ADVS', 'ADVM'])
def news_archive(request: HttpRequest) -> HttpResponse:
    """
    View to show news archive page
    """
    entries = Announcement.objects.filter(created_at__lt=datetime.datetime.now()-datetime.timedelta(days=180), hidden=False, unit__in=request.units)
    return render(request, 'advisornotes/news_archive.html', {'entries': entries})

@requires_role(['ADVS', 'ADVM'])
def view_announcement(request: HttpRequest, entry_id: str) -> HttpResponse:
    """
    View to show individual announcement
    """
    entry = get_object_or_404(Announcement, pk=entry_id, hidden=False, unit__in=request.units)
    return render(request, 'advisornotes/view_announcement.html', {'announcement': entry})

@requires_role(['ADVS', 'ADVM'])
def delete_announcement(request: HttpRequest, entry_id: str) -> HttpResponse:
    if request.method == 'POST':
        entry = get_object_or_404(Announcement, pk=entry_id, unit__in=request.units)
        messages.add_message(request,
                            messages.SUCCESS,
                            'Announcement removed.'
                            )
        l = LogEntry(userid=request.user.username,
                     description="deleted announcement: %s" % (entry),
                     related_object=entry.author
                     )
        l.save()
        entry.hidden = True
        entry.save()
    return HttpResponseRedirect(reverse('advising:news'))


@requires_role(['ADVS', 'ADVM'])
def note_search(request):
    if 'text-search' not in request.GET:
        return ForbiddenResponse(request, "must send search query")
    search = request.GET['text-search']
    query = get_query(search, ('text',))
    notes = AdvisorNote.objects.filter(query, unit__in=request.units) \
            .select_related('student', 'advisor').order_by("-created_at")[:1000]
    note_form = NoteSearchForm(prefix="text", initial={'search': search})
    context = {'notes': notes, 'note_form': note_form}
    return render(request, 'advisornotes/note_search.html', context)


@requires_role(['ADVS', 'ADVM'])
def download_notes_summary(request):
    notes = AdvisorNote.objects.filter(unit__in=request.units).select_related('student', 'advisor')\
        .order_by("-created_at")
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'inline; filename="%s-%s-notes.csv"' % (list(request.units)[0].label,
                                                                              datetime.datetime.now().strftime(
                                                                              '%Y%m%d'))
    writer = csv.writer(response)

    writer.writerow(['Student', 'Advisor', 'Created', 'Has File', 'URL'])
    for note in notes:
        if note.student:
            student = note.student.sortname()
            url = request.build_absolute_uri(reverse('advising:student_notes',
                                                     kwargs={'userid': note.student.userid_or_emplid()}))
        else:
            student = "%s (prospective)" % note.nonstudent.sortname()
            url = request.build_absolute_uri(reverse('advising:student_notes', kwargs={'userid': note.nonstudent.slug}))
        if note.file_attachment:
            attachment = 'Y'
        else:
            attachment = ''
        writer.writerow([student, note.advisor.sortname(), note.created_at.isoformat(), attachment, url])

    return response


@requires_role(['ADVS', 'ADVM'])
def artifact_search(request):
    if 'text-search' not in request.GET:
        return ForbiddenResponse(request, "must send search query")
    search = request.GET['text-search']
    query = get_query(search, ('text',))
    artifact_notes = ArtifactNote.objects.filter(query, unit__in=request.units, hidden=False).order_by("-created_at")[:100]
    for a in artifact_notes:
        if a.course:
            a.url = reverse('advising:view_course_notes', kwargs={'unit_course_slug': a.course.slug})
            a.description = a.course
        elif a.course_offering:
            a.url = reverse('advising:view_offering_notes', kwargs={'course_slug': a.course_offering.slug})
            a.description = a.course_offering
        else:
            a.url = reverse('advising:view_artifact_notes', kwargs={'artifact_slug': a.artifact.slug})
            a.description = a.artifact
    artifact_form = ArtifactSearchForm(prefix="text", initial={'search': search})
    context = {'artifact_notes': artifact_notes, 'artifact_form': artifact_form}
    return render(request, 'advisornotes/artifact_search.html', context)


@requires_role(['ADVS', 'ADVM'])
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


@requires_role(['ADVS', 'ADVM'])
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
    content_html = note.html_content()
    content_text = note.text  # the creole/markdown is good enough for the plain-text version?
    attach = []
    if note.file_attachment:
        note.file_attachment.open()
        attach = [(note.attachment_filename(), note.file_attachment.read(), note.file_mediatype)]

    mail = EmailMultiAlternatives(subject=subject, body=content_text, from_email=from_email, to=[email],
                                  cc=[from_email], attachments=attach)
    mail.attach_alternative(content_html, 'text/html')
    mail.send()


@requires_role(['ADVS', 'ADVM'])
@transaction.atomic
def new_note(request, userid):
    try:
        student = Person.objects.get(find_userid_or_emplid(userid))
    except Person.DoesNotExist:
        student = get_object_or_404(NonStudent, slug=userid)
    unit_choices = [(u.id, str(u)) for u in request.units]

    if request.method == 'POST':
        form = AdvisorNoteForm(data=request.POST, files=request.FILES, student=student)
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
                         description=("new advisor note for %s") % student,
                         related_object=form.instance)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Note created.')

            return _redirect_to_notes(student)
    else:
        form = AdvisorNoteForm(student=student)
        form.fields['unit'].choices = unit_choices
    return render(request, 'advisornotes/new_note.html', {'form': form, 'student': student, 'userid': userid})


@requires_role(['ADVS', 'ADVM'])
@transaction.atomic
def new_artifact_note(request, unit_course_slug=None, course_slug=None, artifact_slug=None):
    unit_choices = [(u.id, str(u)) for u in request.units]
    related = course = offering = artifact = None

    if unit_course_slug != None:
        related = course = get_object_or_404(Course, slug=unit_course_slug)
    elif course_slug != None:
        related = offering = get_object_or_404(CourseOffering, slug=course_slug)
    else:
        related = artifact = get_object_or_404(Artifact, slug=artifact_slug, hidden=False)

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


@requires_role(['ADVS', 'ADVM'])
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
        related = artifact = get_object_or_404(Artifact, slug=artifact_slug, hidden=False)

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


@requires_role(['ADVS', 'ADVM'])
def student_notes(request, userid):
    user = get_object_or_404(Person, userid=request.user.username)
    if not has_photo_agreement(user):
        url = reverse('config:photo_agreement') + '?return=' + urllib.parse.quote(request.path)
        return ForbiddenResponse(request, mark_safe(
            'You must <a href="%s">confirm the photo usage agreement</a> before seeing student photos.' % (url)))

    try:
        student = Person.objects.get(find_userid_or_emplid(userid))
    except Person.DoesNotExist:
        student = get_object_or_404(NonStudent, slug=userid)

    if request.POST and 'note_id' in request.POST:
        # the "hide note" box was checked: process
        note = get_object_or_404(AdvisorNote, pk=request.POST['note_id'], unit__in=Unit.sub_units(request.units))
        note.hidden = request.POST['hide'] == "yes"
        note.save()

    if isinstance(student, Person):
        notes = AdvisorNote.objects.filter(student=student, unit__in=Unit.sub_units(request.units)).order_by("-created_at")
        form_subs = FormSubmission.objects.filter(initiator__sfuFormFiller=student, form__unit__in=Unit.sub_units(request.units),
                                                  form__advisor_visible=True)
        visits = AdvisorVisit.objects.visible(request.units).filter(student=student).order_by('-created_at')
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
        notes = AdvisorNote.objects.filter(nonstudent=student, unit__in=Unit.sub_units(request.units)).order_by("-created_at")
        visits = AdvisorVisit.objects.filter(nonstudent=student, unit__in=request.units).order_by('-created_at')
        for n in notes:
            n.entry_type = 'NOTE'
        items = notes
        nonstudent = True
    
    show_transcript = False
    # For demo purposes only.
    # if 'UNIV' in [u.label for u in request.units]:
    #    show_transcript = True

    template = 'advisornotes/student_notes.html'
    context = {'items': items, 'student': student, 'userid': userid, 'nonstudent': nonstudent,
               'show_transcript': show_transcript, 'units': request.units, 'visits': visits}
    return render(request, template, context)


@requires_role(['ADVS', 'ADVM'])
def download_file(request, userid, note_id):
    note = get_object_or_404(AdvisorNote, id=note_id, unit__in=Unit.sub_units(request.units))
    note.file_attachment.open()
    resp = HttpResponse(note.file_attachment, content_type=note.file_mediatype)
    resp['Content-Disposition'] = 'inline; filename="' + note.attachment_filename() + '"'
    return resp


@requires_role(['ADVS', 'ADVM'])
def download_artifact_file(request, note_id):
    note = get_object_or_404(ArtifactNote, id=note_id, unit__in=request.units)
    note.file_attachment.open()
    resp = HttpResponse(note.file_attachment, content_type=note.file_mediatype)
    resp['Content-Disposition'] = 'inline; filename="' + note.attachment_filename() + '"'
    return resp


@requires_role(['ADVS', 'ADVM'])
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


@requires_role(['ADVS', 'ADVM'])
def student_more_info_short(request, userid):
    """
    Same as above, but with a more limited subset of info.
    """
    student = get_object_or_404(Person, find_userid_or_emplid(userid))
    try:
        data = more_personal_info(student.emplid, needed=['programs', 'gpa', 'citizen', 'gender'])
    except SIMSProblem as e:
        data = {'error': str(e)}

    response = HttpResponse(content_type='application/json')
    json.dump(data, response)
    return response


@requires_role(['ADVS', 'ADVM'])
def student_courses(request, userid):
    """
    List of courses now (and in surrounding semesters)
    """
    student = get_object_or_404(Person, find_userid_or_emplid(userid))
    
    context = {
               'userid': userid,
               'student': student,
               }
    resp = render(request, 'advisornotes/student_courses.html', context)
    resp.has_inline_script = True # show/hide link
    return resp

@requires_role(['ADVS', 'ADVM'])
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
    json.dump(data, response, indent=1)
    return response


@requires_role(['ADVS', 'ADVM'])
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

@requires_role(['ADVS', 'ADVM'])
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
    json.dump(data, response, indent=1)
    return response


@requires_role(['ADVS', 'ADVM'])
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


@requires_role(['ADVS', 'ADVM'])
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


@requires_role(['ADVS', 'ADVM'])
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

    visit = AdvisorVisit(student=student, nonstudent=nonstudent, unit=unit, advisor=advisor,
                         version=ADVISOR_VISIT_VERSION)
    visit.save()
    return HttpResponseRedirect(reverse('advising:edit_visit_initial', kwargs={'visit_slug': visit.slug}))


@requires_role(['ADVS', 'ADVM'])
def edit_visit_initial(request, visit_slug):
    #  This is for the initial edit, when the visit is first created.  At this point, we want to show all the SIMS
    #  stuff, set categories, and also potentially create a note.  The end date/time is set when the form is submitted.
    visit = get_object_or_404(AdvisorVisit, slug=visit_slug, hidden=False)
    already_got_sims = False
    if request.method == 'POST':
        form = AdvisorVisitFormInitial(request.POST, request.FILES, instance=visit)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.categories.clear()
            if 'categories' in form.cleaned_data:
                for c in form.cleaned_data['categories']:
                    visit.categories.add(c)
            visit.end_time = datetime.datetime.now()
            if 'programs' in form.cleaned_data:
                visit.programs = form.cleaned_data['programs']
            if 'cgpa' in form.cleaned_data:
                visit.cgpa = form.cleaned_data['cgpa']
            if 'credits' in form.cleaned_data:
                visit.credits = form.cleaned_data['credits']
            if 'gender' in form.cleaned_data:
                visit.gender = form.cleaned_data['gender']
            if 'citizenship' in form.cleaned_data:
                visit.citizenship = form.cleaned_data['citizenship']
            visit.save()

            if 'note' in form.cleaned_data and form.cleaned_data['note']:
                note = AdvisorNote(student=visit.student, nonstudent=visit.nonstudent, advisor=visit.advisor,
                                   unit=visit.unit, text=form.cleaned_data['note'])
                if 'file_attachment' in request.FILES:
                    upfile = request.FILES['file_attachment']
                    note.file_attachment = upfile
                    note.file_mediatype = upfile.content_type
                if form.cleaned_data['email_student']:
                    _email_student_note(note)
                    note.emailed = True
                note.save()
                l = LogEntry(userid=request.user.username,
                             description=("new advisor note from visit for %s") % visit.get_userid(),
                             related_object=note)
                l.save()
            l = LogEntry(userid=request.user.username,
                         description=("Recorded visit for %s") % visit.get_userid(),
                         related_object=visit)
            l.save()
            script = '<script nonce='+request.csp_nonce+'>window.close();window.opener.location.reload();</script>'
            return HttpResponse(script)
    else:
        form = AdvisorVisitFormInitial(instance=visit)
        #  If we've already fetched info from SIMS for this person, set a flag so we don't automatically fetch it again,
        #  this would mean we're editing an already populated visit, and we should leave the choice to the user.
        if visit.cgpa:
            form.initial['cgpa'] = visit.cgpa
            already_got_sims = True
        if visit.programs:
            form.initial['programs'] = visit.programs
            already_got_sims = True
        if visit.credits:
            form.initial['credits'] = visit.credits
            already_got_sims = True

    return render(request, 'advisornotes/record_visit.html', {'userid': visit.get_userid(), 'visit': visit,
                                                              'form': form,
                                                              'fetch_automatically': not already_got_sims})


@requires_role('ADVM')
def edit_visit_admin(request, visit_slug):
    return edit_visit_subsequent(request, visit_slug, admin=True)


@requires_role(['ADVS', 'ADVM'])
def edit_visit_subsequent(request, visit_slug, admin=False):
    #  This is for advisors to edit their own visits, or advisor managers to edit those of their teams.  The only
    #  real use case right now is someone forgetting to end a visit, and having the advisor/manager set the end time
    #  correctly.
    visit = get_object_or_404(AdvisorVisit, slug=visit_slug, hidden=False)
    requester = get_object_or_404(Person, userid=request.user.username)
    # Managers can edit all visits in their unit, and advisors can edit their own visits.
    if (admin and not Role.objects.filter(person=requester, role='ADVM', unit=visit.unit).exists()) or \
            (not admin and not visit.advisor == requester):
        return ForbiddenResponse(request, "You do not have permission to edit this visit.")
    if request.method == 'POST':
        form = AdvisorVisitFormSubsequent(request.POST, instance=visit)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.categories.clear()
            if 'categories' in form.cleaned_data:
                for c in form.cleaned_data['categories']:
                    visit.categories.add(c)
            visit.save()
            l = LogEntry(userid=request.user.username,
                         description=("Edited visit for %s") % visit.get_userid(),
                         related_object=visit)
            l.save()
            if admin:
                return HttpResponseRedirect(reverse('advising:all_visits'))
            else:
                return HttpResponseRedirect(reverse('advising:my_visits'))
    else:
        form = AdvisorVisitFormSubsequent(instance=visit)
    return render(request, 'advisornotes/edit_visit.html', {'userid': visit.get_userid(), 'visit': visit,
                                                            'form': form, 'admin': admin})


@requires_role(['ADVS', 'ADVM'])
def view_visit(request, visit_slug):
    visit = AdvisorVisit.objects.visible(request.units).get(slug=visit_slug)
    return render(request, 'advisornotes/view_visit.html', {'userid': visit.get_userid(), 'visit': visit})


@requires_role('ADVM')
def all_visits(request):
    visits = AdvisorVisit.objects.visible(request.units).select_related('student', 'nonstudent', 'advisor', )\
                 .prefetch_related('categories').order_by("-created_at")[:5000]
    context = {'visits': visits, 'admin': True}
    return render(request, 'advisornotes/all_visits.html', context)


@requires_role(['ADVS', 'ADVM'])
def my_visits(request):
    #  Same as all visits, but for a given advisor.
    advisor = get_object_or_404(Person, userid=request.user.username)
    visits = AdvisorVisit.objects.visible(request.units).filter(advisor=advisor)\
        .select_related('student', 'nonstudent', 'advisor').prefetch_related('categories')\
        .order_by("-created_at")[:5000]
    context = {'visits': visits, 'mine': True}
    return render(request, 'advisornotes/all_visits.html', context)


@requires_role('ADVM')
def download_all_visits(request):
    visits = AdvisorVisit.objects.visible(request.units).select_related('student', 'nonstudent', 'advisor', ) \
                 .prefetch_related('categories').order_by("-created_at")[:5000]
    return _return_visits_csv(visits=visits, admin=True)


@requires_role(['ADVS', 'ADVM'])
def download_my_visits(request):
    advisor = get_object_or_404(Person, userid=request.user.username)
    visits = AdvisorVisit.objects.visible(request.units).filter(advisor=advisor) \
                 .select_related('student', 'nonstudent', 'advisor').prefetch_related('categories') \
                 .order_by("-created_at")[:5000]
    return _return_visits_csv(visits=visits, admin=False)


def _return_visits_csv(visits=None, admin=False):
    response = HttpResponse(content_type='text/csv')
    if admin:
        filename_prefix = 'all'
    else:
        filename_prefix = 'my'

    response['Content-Disposition'] = 'inline; filename="%s-%s-visits.csv"' % \
                                      (datetime.datetime.now().strftime('%Y%m%d'), filename_prefix)
    writer = csv.writer(response)

    writer.writerow(['Start', 'End', 'Duration', 'Mode', 'Campus', 'Student', 'Advisor', 'Categories', 'Programs', 'CGPA',
                     'Credits', 'Gender', 'Citizenship'])
    for v in visits:
        writer.writerow([v.get_created_at_display(), v.get_end_time_display(), v.get_duration(), v.get_mode_display(), v.get_campus_display(),
                         v.get_full_name(), v.advisor.sortname_pref_only(), v.categories_display(), v.programs, v.cgpa, v.credits,
                         v.gender, v.citizenship])
    return response

@require_POST
@requires_role(['ADVS', 'ADVM'])
def end_visit_mine(request, visit_slug):
    advisor = get_object_or_404(Person, userid=request.user.username)
    visit = get_object_or_404(AdvisorVisit, slug=visit_slug, unit__in=request.units, advisor=advisor, hidden=False)
    visit.end_time = datetime.datetime.now()
    visit.save()
    l = LogEntry(userid=request.user.username,
                 description=("manually ended own advisor visit for %s from %s") % (visit.get_userid(), visit.created_at),
                 related_object=visit)
    l.save()
    return HttpResponseRedirect(reverse('advising:my_visits'))


@require_POST
@requires_role('ADVM')
def end_visit_admin(request, visit_slug):
    visit = get_object_or_404(AdvisorVisit, slug=visit_slug, unit__in=request.units, hidden=False)
    visit.end_time = datetime.datetime.now()
    visit.save()
    l = LogEntry(userid=request.user.username,
                 description=("manually ended advisor visit for %s with %s from %s") %
                             (visit.get_userid(), visit.advisor.userid, visit.created_at),
                 related_object=visit)
    l.save()
    return HttpResponseRedirect(reverse('advising:all_visits'))


@require_POST
@requires_role(['ADVS', 'ADVM'])
def delete_visit_mine(request, visit_slug):
    advisor = get_object_or_404(Person, userid=request.user.username)
    visit = get_object_or_404(AdvisorVisit, slug=visit_slug, unit__in=request.units, advisor=advisor, hidden=False)
    visit.hidden = True
    visit.save()
    l = LogEntry(userid=request.user.username,
                 description=("deleted own advisor visit for %s from %s") % (visit.get_userid(), visit.created_at),
                 related_object=visit)
    l.save()
    return HttpResponseRedirect(reverse('advising:my_visits'))


@require_POST
@requires_role('ADVM')
def delete_visit_admin(request, visit_slug):
    visit = get_object_or_404(AdvisorVisit, slug=visit_slug, unit__in=request.units, hidden=False)
    visit.hidden = True
    visit.save()
    l = LogEntry(userid=request.user.username,
                 description=("deleted advisor visit via admin for %s with %s from %s") %
                             (visit.get_userid(), visit.advisor.userid, visit.created_at),
                 related_object=visit)
    l.save()
    return HttpResponseRedirect(reverse('advising:all_visits'))

@requires_role(['ADVS', 'ADVM'])
def view_nonstudents(request):
    start = datetime.datetime.now() - datetime.timedelta(days=365)
    nonstudents = NonStudent.objects.filter(unit__in=request.units, created_at__isnull=False, created_at__gte=start)
    context = {'nonstudents': nonstudents}
    return render(request, 'advisornotes/view_nonstudents.html', context)

@requires_role(['ADVS', 'ADVM'])
@transaction.atomic
def new_nonstudent(request: HttpRequest) -> HttpResponse:
    """
    View to create a new non-student
    """
    unit_choices = [(u.id, str(u)) for u in request.units]
    if request.POST:
        form = NonStudentForm(request.POST)
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            nonstudent = form.save(commit=False)
            nonstudent.created_at = datetime.datetime.now()
            nonstudent = form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("new prospective student %s by %s") % (NonStudent, request.user.username),
                  related_object=form.instance)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Prospective Student "%s" Created.' % nonstudent)
            return _redirect_to_notes(nonstudent)
    else:
        form = NonStudentForm()
        form.fields['unit'].choices = unit_choices
    return render(request, 'advisornotes/new_nonstudent.html', {'form': form})

@requires_role(['ADVS', 'ADVM'])
@transaction.atomic
def edit_nonstudent(request: HttpRequest, nonstudent_slug: str) -> HttpResponse:
    """
    View to edit a non-student
    """
    nonstudent = get_object_or_404(NonStudent, slug=nonstudent_slug, unit__in=request.units)
    unit_choices = [(u.id, str(u)) for u in request.units]
    if request.POST:
        form = NonStudentForm(request.POST, instance=nonstudent)
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            nonstudent = form.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edited nonstudent %s by %s") % (nonstudent, request.user.username),
                  related_object=form.instance)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Prospective Student "%s" edited.' % nonstudent)
            return _redirect_to_notes(nonstudent)
    else:
        form = NonStudentForm(instance=nonstudent)
        form.fields['unit'].choices = unit_choices
    return render(request, 'advisornotes/edit_nonstudent.html', {'form': form, 'nonstudent': nonstudent})

@requires_role(['ADVS', 'ADVM'])
def download_nonstudents(request: HttpRequest) -> HttpResponse:
    """
    View to download nonstudents
    """
    start = datetime.datetime.now() - datetime.timedelta(days=365)
    nonstudents = NonStudent.objects.filter(unit__in=request.units, created_at__isnull=False, created_at__gte=start)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'inline; filename="prospective-students-%s.csv"' % (datetime.datetime.now().strftime('%Y%m%d'))
    writer = csv.writer(response)

    writer.writerow(['First Name', 'Last Name', 'Middle Name', 'Gender', 'Email Address', 
                     'High School', 'College', 'Start Year', 'Potential Program', 'Preferred Campus', 'Unit', 'Created At'])
    for ns in nonstudents:
        writer.writerow([ns.first_name, ns.last_name, ns.middle_name, ns.gender, ns.email_address,
                        ns.high_school, ns.college, ns.start_year, ns.program, ns.campus, ns.unit, ns.created_at.date()])

    return response


@requires_role(['ADVS', 'ADVM'])
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


@requires_role(['ADVS', 'ADVM'])
@transaction.atomic
def edit_artifact(request, artifact_slug):
    """
    View to edit a new artifact
    """
    artifact = get_object_or_404(Artifact, slug=artifact_slug, hidden=False)
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

@requires_role(['ADVS', 'ADVM'])
def view_artifacts(request):
    """
    View to view all unretired artifacts
    """
    artifacts = Artifact.objects.filter(unit__in=request.units, hidden=False)
    return render(request,
        'advisornotes/view_artifacts.html',
        {'artifacts': artifacts}
    )

@requires_role(['ADVS', 'ADVM'])
def view_retired_artifacts(request):
    """
    View to view all retired artifacts
    """
    retired_artifacts = Artifact.objects.filter(unit__in=request.units, hidden=True)
    return render(request,
        'advisornotes/view_retired_artifacts.html',
        {'retired_artifacts': retired_artifacts}
    )

@requires_role(['ADVS', 'ADVM'])
def delete_artifact(request: HttpRequest, artifact_slug: str) -> HttpResponse:
    """
    View to hide an artifact
    """
    if request.method == 'POST':
        artifact = get_object_or_404(Artifact, slug=artifact_slug)
        messages.add_message(request,
                            messages.SUCCESS,
                            'Artifact retired'
                            )
        l = LogEntry(userid=request.user.username,
                     description="retired artifact: %s" % (artifact),
                     related_object=artifact
                     )
        l.save()
        artifact.hidden = True
        artifact.save()
    return HttpResponseRedirect(reverse('advising:view_artifacts'))

@requires_role(['ADVS', 'ADVM'])
def view_artifact_notes(request, artifact_slug):
    """
    View to view all notes for a specific artifact
    """
    artifact = get_object_or_404(Artifact, slug=artifact_slug, unit__in=request.units)
    retired = artifact.hidden
    notes = ArtifactNote.objects.filter(artifact__slug=artifact_slug).order_by('category', 'created_at')
    important_notes = notes.filter(important=True)
    notes = notes.exclude(important=True)
    return render(request,
        'advisornotes/view_artifact_notes.html',
        {'artifact': artifact, 'notes': notes, 'important_notes': important_notes, 'retired': retired}
    )


@requires_role(['ADVS', 'ADVM'])
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


@requires_role(['ADVS', 'ADVM'])
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


@requires_role(['ADVS', 'ADVM'])
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


@requires_role(['ADVS', 'ADVM'])
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


@requires_role(['ADVS', 'ADVM'])
def view_all_semesters(request):
    """
    View to view all semesters
    """
    semesters = Semester.objects.all()
    return render(request,
        'advisornotes/view_all_semesters.html',
        {'semesters': semesters}
    )


@requires_role(['ADVS', 'ADVM'])
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


@requires_role(['ADVS', 'ADVM'])
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


@requires_role(['ADVS', 'ADVM'])
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
            visits = AdvisorVisit.objects.filter(nonstudent=nonstudent)
            for note in notes:
                note.nonstudent = None
                note.student = student
                note.save()
            if nonstudent.high_school:
                student.set_nonstudent_hs(nonstudent.high_school)
            if nonstudent.college:
                student.set_nonstudent_colg(nonstudent.college)
            student.set_nonstudent_notes("Previously a prospective student, merged on " + str(datetime.datetime.today().date()) + ". " + nonstudent.notes)
            # If we had an email address for this nonstudent, store it in the application email address, like
            # for a grad student.  We really don't have a better place to store this.  The other option would be
            # to drop it altogether.
            if nonstudent.email_address:
                student.config['applic_email'] = nonstudent.email_address
            for visit in visits:
                visit.nonstudent = None
                visit.student = student
                visit.save()
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


@requires_role('ADVM')
def manage_categories(request):
    categories = AdvisorVisitCategory.objects.visible(request.units)
    return render(request, 'advisornotes/manage_categories.html', {'categories': categories})


@requires_role('ADVM')
@transaction.atomic
def add_category(request):
    if request.method == 'POST':
        form = AdvisorVisitCategoryForm(request, request.POST)
        if form.is_valid():
            category = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'Added category %s' % category)
            l = LogEntry(userid=request.user.username,
                         description="Added category %s" % category,
                         related_object=category)
            l.save()
            return HttpResponseRedirect(reverse('advising:manage_categories'))
    else:
        form = AdvisorVisitCategoryForm(request)
    return render(request, 'advisornotes/add_category.html', {'form': form})


@requires_role('ADVM')
@transaction.atomic
def edit_category(request, category_slug):
    category = get_object_or_404(AdvisorVisitCategory, slug=category_slug, unit__in=request.units)
    if request.method == 'POST':
        form = AdvisorVisitCategoryForm(request, request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 'Edited category %s' % category)
            l = LogEntry(userid=request.user.username,
                         description="Edited category %s" % category,
                         related_object=category)
            l.save()
            return HttpResponseRedirect(reverse('advisornotes:manage_categories'))
    else:
        form = AdvisorVisitCategoryForm(request, instance=category)
    return render(request, 'advisornotes/edit_category.html', {'form': form, 'category_slug': category.slug})


@requires_role('ADVM')
@transaction.atomic
def delete_category(request, category_slug):
    category = get_object_or_404(AdvisorVisitCategory, slug=category_slug, unit__in=request.units)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Deleted category %s' % category)
        l = LogEntry(userid=request.user.username,
                     description="Deleted category: %s" % category,
                     related_object=category)
        l.save()
    return HttpResponseRedirect(reverse('advising:manage_categories'))
