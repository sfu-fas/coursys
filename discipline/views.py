import datetime
import itertools
import csv
import re
from typing import Any, Dict

from django.db import transaction
from django.forms import Form
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest, HttpResponseNotAllowed, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.template import defaultfilters
from django.contrib import messages
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from coredata.models import Member, CourseOffering, Person, Role, Unit
from django.views.decorators.cache import cache_page
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from discipline.models import DisciplineCaseBase, DisciplineCaseInstrStudent, DisciplineCaseInstrNonStudent, \
    DisciplineGroup, MAX_ATTACHMENTS, MAX_ATTACHMENTS_TEXT, DisciplineCaseInstr, DisciplineCaseChair, DisciplineTemplate,\
    CaseAttachment, RESPONSE_CHOICES
from discipline.forms import DisciplineGroupForm, DisciplineCaseForm, DisciplineInstrNonStudentCaseForm, \
    NewAttachFileForm, EditAttachFileForm, CaseCentralNoteForm, DisciplineRoleForm, TemplateForm, \
    NotifyEmailForm, FactsForm, PenaltyForm, SendForm, NotesForm
from log.models import LogEntry
from courselib.auth import requires_discipline_user, is_discipline_user, requires_role, requires_global_role, ForbiddenResponse
from django.contrib.auth.decorators import login_required


also_set_re = re.compile(r"also-(?P<field>[a-z_]+)-(?P<caseid>\d+)")


@requires_discipline_user
def index(request, course_slug):
    """
    Instructor's list of cases for the course
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    student_cases = DisciplineCaseInstrStudent.objects.filter(offering=course) \
        .select_related('owner', 'offering', 'offering__owner', 'offering__semester', 'group', 'student')
    nonstudent_cases = DisciplineCaseInstrNonStudent.objects.filter(offering=course) \
        .select_related('owner', 'offering', 'offering__owner', 'offering__semester', 'group')
    cases = itertools.chain(student_cases, nonstudent_cases)

    groups = DisciplineGroup.objects.filter(offering=course)

    context = {'course': course, 'cases': cases, 'groups': groups}
    return render(request, "discipline/index.html", context)


@requires_discipline_user
def newgroup(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    drop_cutoff = course.semester.start.isoformat()  # assume students can't get into too much trouble before the semester start
    student_choices = [
            (m.person.userid,
               "%s (%s, %s%s)" % (m.person.sortname(), m.person.emplid, m.person.userid,
                                  ', dropped' if m.role == 'DROP' else ''))
            for m in
            Member.objects.filter(offering=course, role__in=["STUD", "DROP"]).select_related('person')
            if m.role == 'STUD' or ('drop_date' in m.config and m.config['drop_date'] > drop_cutoff)]

    if request.method == 'POST':
        form = DisciplineGroupForm(offering=course, data=request.POST)
        form.fields['students'].choices = student_choices
        if form.is_valid():
            instructor = Person.objects.get(userid=request.user.username)
            group = form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("created a discipline cluster in %s") % (course),
                  related_object=group)
            l.save()
            for userid in form.cleaned_data['students']:
                # create case for each student in the group
                student = Member.objects.get(offering=course, person__userid=userid)
                case = DisciplineCaseInstrStudent(student=student.person, group=group, owner=instructor, offering=course)
                case.save()
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("created a discipline case for %s in cluster %s") % (userid, group.name),
                      related_object=case)
                l.save()
            return HttpResponseRedirect(reverse('offering:discipline:showgroup', kwargs={'course_slug': course_slug, 'group_slug': group.slug}))

    else:
        form = DisciplineGroupForm(offering=course)

    form.fields['students'].choices = student_choices
    context = {'course': course, 'form': form}
    return render(request, "discipline/newgroup.html", context)


@requires_discipline_user
def new(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    drop_cutoff = course.semester.start.isoformat()  # assume students can't get into too much trouble before the semester start
    student_choices = [
            (m.person.userid,
               "%s (%s, %s%s)" % (m.person.sortname(), m.person.emplid, m.person.userid,
                                  ', dropped' if m.role == 'DROP' else ''))
            for m in
            Member.objects.filter(offering=course, role__in=["STUD", "DROP"]).select_related('person')
            if m.role == 'STUD' or ('drop_date' in m.config and m.config['drop_date'] > drop_cutoff)]
    group_choices = [('', '\u2014')] + [(g.id, g.name) for g in DisciplineGroup.objects.filter(offering=course)]

    if request.method == 'POST':
        form = DisciplineCaseForm(offering=course, data=request.POST)
        form.fields['student'].choices = student_choices
        form.fields['group'].choices = group_choices
        if form.is_valid():
            instructor = Person.objects.get(userid=request.user.username)
            case = form.save(commit=False)
            case.owner = instructor
            case.offering = course
            case.save()
            form.save_m2m()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("created a discipline case for %s in %s") % (case.student.name(), course),
                  related_object=case)
            l.save()
            return HttpResponseRedirect(reverse('offering:discipline:show', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))

    else:
        form = DisciplineCaseForm(offering=course)

    form.fields['student'].choices = student_choices
    form.fields['group'].choices = group_choices
    context = {'course': course, 'form': form}
    return render(request, "discipline/new.html", context)


@requires_discipline_user
def new_nonstudent(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    group_choices = [('', '\u2014')] + [(g.id, g.name) for g in DisciplineGroup.objects.filter(offering=course)]

    if request.method == 'POST':
        form = DisciplineInstrNonStudentCaseForm(data=request.POST)
        form.fields['group'].choices = group_choices
        if form.is_valid():
            instructor = Person.objects.get(userid=request.user.username)
            case = form.save(commit=False)
            case.owner = instructor
            case.offering = course
            case.slug = defaultfilters.slugify(case.first_name + " " + case.last_name)
            case.save()
            form.save_m2m()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("created a non-student discipline case for %s in %s") % (case.student.name(), course),
                  related_object=case)
            l.save()
            return HttpResponseRedirect(reverse('offering:discipline:show', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))

    else:
        form = DisciplineInstrNonStudentCaseForm()

    form.fields['group'].choices = group_choices
    context = {'course': course, 'form': form}
    return render(request, "discipline/new_nonstudent.html", context)


@requires_discipline_user
def show(request, course_slug, case_slug):
    """
    Display current case status
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug)
    case = case.subclass()
    roles = request.session['discipline-'+course_slug]  # get roles from session
    if case.public_attachments_size() > MAX_ATTACHMENTS:
        messages.add_message(request, messages.WARNING, 'Total size of public attachments must be at most %s because of email limitations. Please make some of the attachments private.' % (MAX_ATTACHMENTS_TEXT,))

    context = {'course': course, 'case': case, 'roles': roles}
    return render(request, "discipline/show.html", context)


@requires_discipline_user
def showgroup(request, course_slug, group_slug):
    """
    Display current case status
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    group = get_object_or_404(DisciplineGroup, slug=group_slug, offering__slug=course_slug)

    context = {'course': course, 'group': group}
    return render(request, "discipline/showgroup.html", context)


class CaseEditView(TemplateView):
    offering: CourseOffering
    case: DisciplineCaseBase
    field: str
    edit_form: type

    @method_decorator(requires_discipline_user)
    @transaction.atomic
    def dispatch(self, request: HttpRequest, course_slug: str, case_slug: str) -> HttpResponse:
        self.offering = get_object_or_404(CourseOffering, slug=course_slug)
        case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug)
        self.case = case.subclass()

        # permission checks
        roles = self.request.session['discipline-' + course_slug]
        if self.request.method == 'POST' and not self.case.can_edit(self.field):
            # once instructor finished, don't allow editing those fields
            return ForbiddenResponse(request, "letter has been sent: cannot edit this field")
        elif isinstance(self.case, DisciplineCaseInstr) and "INSTR" not in roles:
            # only instructor can edit those fields
            return ForbiddenResponse(request, "only the instructor can edit this field")
        elif isinstance(self.case, DisciplineCaseChair) and "DEPT" not in roles:
            # only discipline admins can edit chair fields
            return ForbiddenResponse(request, "only the Chair (or delegate) can edit this field")

        if request.method == 'GET' and self.template_name is None:
            return HttpResponseNotAllowed(self._allowed_methods())

        return super().dispatch(request, course_slug, case_slug)

    def get_context_data(self) -> Dict[str, Any]:
        form = self.edit_form(case=self.case, initial=self.initial_data())

        return {
            'offering': self.offering,
            'case': self.case,
            'form': form,
            'currentuser': Person.objects.get(userid=self.request.user.username),
        }

    def initial_data(self) -> Dict[str, Any]:
        raise NotImplementedError()

    @staticmethod
    def handle(request: HttpRequest, case: DisciplineCaseInstr, form: Form) -> None:
        """
        Handle submission of the for for *this* case. May be called multiple times when instructor selects "also for".
        """
        raise NotImplementedError()

    def post(self, request, *args, **kwargs):
        form = self.edit_form(case=self.case, data=request.POST)
        if form.is_valid():
            self.handle(request, self.case, form)
            if 'also_for' in form.cleaned_data:
                for c in form.cleaned_data['also_for']:
                    if c.can_edit(self.field):
                        self.handle(request, c, form)
            return redirect('offering:discipline:show', course_slug=self.case.offering.slug, case_slug=self.case.slug)

        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


class CaseNotify(CaseEditView):
    field = 'contact_email_text'
    template_name = 'discipline/new_edit_notify.html'
    edit_form = NotifyEmailForm

    @staticmethod
    def handle(request: HttpRequest, case: DisciplineCaseInstr, form: Form) -> None:
        case.contact_email_text = form.cleaned_data['contact_email_text']
        case.contacted = 'MAIL'
        case.contact_date = datetime.date.today()
        case.save()
        case.send_contact_email()
        messages.add_message(request, messages.INFO, f"Email sent to {case.student.email()} notifying of case.")

    def initial_data(self) -> Dict[str, Any]:
        return {'contact_email_text': self.case.contact_email_text}

    def post(self, request, *args, **kwargs):
        if 'notify' in request.POST and request.POST['notify'] in ['NONE', 'OTHR']:
            self.case.contacted = request.POST['notify']
            self.case.save()
            return redirect('offering:discipline:show', course_slug=self.case.offering.slug, case_slug=self.case.slug)
        # else: form submission

        form = self.edit_form(case=self.case, data=request.POST)
        if form.is_valid():
            self.handle(request, self.case, form)
            if 'also_for' in form.cleaned_data:
                for c in form.cleaned_data['also_for']:
                    if c.can_edit(self.field):
                        self.handle(request, c, form)
            return redirect('offering:discipline:show', course_slug=self.case.offering.slug, case_slug=self.case.slug)

        context = self.get_context_data()
        context['form'] = form
        return self.render_to_response(context)


class CaseResponse(CaseEditView):
    field = 'response'
    template_name = None
    edit_form = None

    def initial_data(self):
        return {}

    @staticmethod
    def handle(request, case, form):
        pass

    def post(self, request, *args, **kwargs):
        if 'response' in request.POST and request.POST['response'] in dict(RESPONSE_CHOICES).keys():
            self.case.response = request.POST['response']
            if self.case.response not in ['WAIT', 'NONE']:
                self.case.meeting_date = datetime.date.today()
            else:
                self.case.meeting_date = None
            self.case.save()

        return redirect('offering:discipline:show', course_slug=self.case.offering.slug, case_slug=self.case.slug)


class CaseFacts(CaseEditView):
    field = 'facts'
    template_name = 'discipline/new_edit_facts.html'
    edit_form = FactsForm

    def initial_data(self):
        return {
            'facts': [self.case.facts, self.case.config.get('facts_markup', 'textile'), False],
            'weight': self.case.config.get('weight', ''),
            'mode': self.case.config.get('mode', 'NOAN'),
        }

    @staticmethod
    def handle(request: HttpRequest, case: DisciplineCaseInstr, form: Form) -> None:
        case.facts = form.cleaned_data['facts'][0]
        case.config['facts_markup'] = form.cleaned_data['facts'][1]
        case.config['weight'] = form.cleaned_data['weight']
        case.config['mode'] = form.cleaned_data['mode']
        case.save()
        messages.add_message(request, messages.INFO, f"Updated facts for {case.full_name()}.")


class CasePenalty(CaseEditView):
    field = 'penalty'
    template_name = 'discipline/new_edit_penalty.html'
    edit_form = PenaltyForm

    def initial_data(self):
        return {
            'penalty': self.case.penalty.split(','),
            'refer': self.case.refer,
            'penalty_reason': [self.case.penalty_reason, self.case.config.get('penalty_reason_markup', 'textile'), False]
        }

    @staticmethod
    def handle(request: HttpRequest, case: DisciplineCaseInstr, form: Form) -> None:
        case.penalty = form.cleaned_data['penalty']
        case.refer = form.cleaned_data['refer']
        case.penalty_reason = form.cleaned_data['penalty_reason'][0]
        case.config['penalty_reason_markup'] = form.cleaned_data['penalty_reason'][1]
        case.save()
        messages.add_message(request, messages.INFO, f"Updated penalty for {case.full_name()}.")


class CaseSend(CaseEditView):
    field = 'sent'
    template_name = 'discipline/new_edit_send.html'
    edit_form = SendForm

    def initial_data(self):
        return {
            'letter_review': self.case.letter_review
        }

    @staticmethod
    def handle(request: HttpRequest, case: DisciplineCaseInstr, form: Form) -> None:
        assert case.public_attachments_size() <= MAX_ATTACHMENTS  # should be ensured by "review letter" step
        case.send_letter(_currentuser(request))
        messages.add_message(request, messages.INFO, "Letter sent to student summarizing case.")


class CaseNotes(CaseEditView):
    field = 'notes'
    template_name = 'discipline/new_edit_notes.html'
    edit_form = NotesForm

    def initial_data(self):
        return {
            'notes': [self.case.notes, self.case.config.get('notes_markup', 'textile'), False]
        }

    @staticmethod
    def handle(request: HttpRequest, case: DisciplineCaseInstr, form: Form) -> None:
        case.notes = form.cleaned_data['notes'][0]
        case.config['notes_markup'] = form.cleaned_data['notes'][1]
        case.save()
        messages.add_message(request, messages.INFO, f"Updated notes for {case.full_name()}.")


class CasePenaltyImplemented(CaseEditView):
    field = 'penalty_implemented'
    template_name = None
    edit_form = None

    def initial_data(self):
        return {}

    @staticmethod
    def handle(request, case, form):
        pass

    def post(self, request, *args, **kwargs):
        if 'penalty_implemented' in request.POST:
            self.case.penalty_implemented = request.POST['penalty_implemented'] == 'yes'
            self.case.save()

        return redirect('offering:discipline:show', course_slug=self.case.offering.slug, case_slug=self.case.slug)


@csrf_exempt
@cache_page(3600)
@requires_discipline_user
def markup_preview(request: HttpRequest, course_slug: str) -> JsonResponse:
    from courselib.markup import markup_to_html
    try:
        try:
            content, markup, math = request.GET['content'], request.GET['markup'], request.GET['math'] == 'true'
        except KeyError:
            content, markup, math = request.POST['content'], request.POST['markup'], request.POST['math'] == 'true'
        html = markup_to_html(content, markup, math=math, restricted=True, forum_links=False)
        return JsonResponse({'html': html})
    except:  # yes I'm catching anything: any failure is low-consequence, so let it go.
        return JsonResponse({'html': ''})


def _currentuser(request):
    """
    Return Person associated with the current request
    """
    return Person.objects.get(userid=request.user.username)


@login_required
def view_letter(request, course_slug, case_slug):
    """
    Display current case status
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug)
    case = case.subclass()

    # allowed users: instructor/discipline admin, or student if they received the letter.
    if is_discipline_user(request, course_slug):
        is_student = False
        messages.add_message(request, messages.INFO,
                "The student should be able to view the letter at this URL as well." )
    elif request.user.username == case.student.userid and case.letter_sent == 'MAIL':
        is_student = True
    else:
        return ForbiddenResponse(request)

    if case.letter_sent != 'MAIL' or not case.letter_text:
        return ForbiddenResponse(request, errormsg="The letter for this case was not sent by this system.")

    context = {'course': course, 'case': case, 'is_student': is_student}
    return render(request, "discipline/view_letter.html", context)


# Attachment editing views

@requires_discipline_user
def edit_attach(request, course_slug, case_slug):
    """
    Front page of the file attachments interface
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug)
    case = case.subclass()
    attach_pub = CaseAttachment.objects.filter(case=case, public=True)
    attach_pri = CaseAttachment.objects.filter(case=case, public=False)

    if not case.can_edit('attach'):
        # once case is closed, don't allow editing
        return ForbiddenResponse(request)

    groupmembersJSON = case.groupmembersJSON()
    context = {'course': course, 'case': case, 'attach_pub': attach_pub, 'attach_pri': attach_pri,
            'templatesJSON': '[]', 'groupmembersJSON': mark_safe(groupmembersJSON)}
    return render(request, "discipline/show_attach.html", context)


@requires_discipline_user
def new_file(request, course_slug, case_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug)
    case = case.subclass()

    if not case.can_edit('attach'):
        # once case is closed, don't allow editing
        return ForbiddenResponse(request)

    if request.method == 'POST':
        form = NewAttachFileForm(case, request.POST, request.FILES)
        if form.is_valid():
            f = form.save()
            mediatype = request.FILES['attachment'].content_type
            f.mediatype = mediatype
            f.save()

            case.letter_review = False
            case.letter_sent = 'WAIT'
            case.penalty_implemented = False
            case.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edit discipline case %s in %s: add attachment %s") % (case.slug, case.offering, f.name),
                  related_object=case)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Created file attachment "%s".' % (f.name))
            return HttpResponseRedirect(reverse('offering:discipline:edit_attach', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))
    else:
        form = NewAttachFileForm(case)

    context = {'course': course, 'case': case, 'form': form}
    return render(request, "discipline/new_file.html", context)


@login_required
def download_file(request, course_slug, case_slug, fileid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug)
    case = case.subclass()
    attach = get_object_or_404(CaseAttachment, case__slug=case_slug, case__offering__slug=course_slug, id=fileid)

    # allowed users: instructor/discipline admin, or student if they received the letter.
    if is_discipline_user(request, course_slug):
        is_student = False
    elif attach.public and request.user.username == case.student.userid and case.letter_sent == 'MAIL':
        is_student = True
    else:
        return ForbiddenResponse(request)

    if is_student and (case.letter_sent != 'MAIL' or not case.letter_text):
        return ForbiddenResponse(request, errormsg="The letter for this case was not sent by this system.")

    attach.attachment.open()
    resp = HttpResponse(attach.attachment, content_type=attach.mediatype)
    resp['Content-Disposition'] = 'inline; filename="' + attach.filename() + '"'

    return resp


class CaseDeleteAttachment(CaseEditView):
    field = None
    template_name = None
    edit_form = None

    def initial_data(self):
        raise NotImplementedError()

    @staticmethod
    def handle(request, case, form):
        raise NotImplementedError()

    def post(self, request, *args, **kwargs):
        if 'delete_attachment' in request.POST:
            attachment = get_object_or_404(CaseAttachment, case__slug=self.case.slug, case__offering__slug=self.case.offering.slug,
                                           id=request.POST['delete_attachment'])
            case = attachment.case
            id = attachment.id
            attachment.delete()

            # LOG EVENT#
            l = LogEntry(userid=request.user.username,
                         description=("eddit discipline case %s in %s: delete attachment %s") % (
                         case.slug, case.offering, id),
                         related_object=case)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Deleted file attachment.')

        return redirect('offering:discipline:edit_attach', course_slug=self.case.offering.slug, case_slug=self.case.slug)


# Discipline chair/admin views

def __chair_cases(request):
    # discipline admin for these departments
    subunit_ids = Unit.sub_unit_ids(request.units)
    has_global_role = 'UNIV' in (u.label for u in request.units)

    instr_student_cases = DisciplineCaseInstrStudent.objects.filter(offering__owner__id__in=subunit_ids) \
        .select_related('owner', 'offering', 'offering__owner', 'offering__semester', 'group', 'student')
    instr_nonstudent_cases = DisciplineCaseInstrNonStudent.objects.filter(offering__owner__id__in=subunit_ids) \
        .select_related('owner', 'offering', 'offering__owner', 'offering__semester', 'group')
    instr_cases = itertools.chain(instr_student_cases, instr_nonstudent_cases)

    # can see cases either (1) in your unit, or (2) in subunits if the letter has been sent
    instr_cases = [c for c in instr_cases if (c.offering.owner in request.units) or (c.letter_sent != 'WAIT')]
    return instr_cases, has_global_role


@requires_role("DISC")
def chair_index(request):
    instr_cases, has_global_role = __chair_cases(request)
    context = {'instr_cases': instr_cases, 'has_global_role': has_global_role}
    return render(request, "discipline/chair-index.html", context)


@requires_role("DISC")
def chair_csv(request):
    instr_cases, has_global_role = __chair_cases(request)
    response = HttpResponse(
        content_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'inline; filename="dishonesty_cases.csv"'},
    )
    instr_cases.sort(key=lambda c: (c.offering.semester.name, c.offering.name(), c.student.sortname()))
    writer = csv.writer(response)
    writer.writerow(['Student Name', 'Emplid', 'Email', 'Case Cluster', 'Semester', 'Course', 'Instructor', 'Instr Email', 'Offering Mode', 'Mode (instr provided)'])
    for c in instr_cases:
        writer.writerow([
            c.student.sortname(), c.student.emplid, c.student.email(),
            c.group.name if c.group else None,
            c.offering.semester.name,
            c.offering.name(),
            c.owner.sortname(),
            c.owner.email(),
            c.offering.get_mode_display(),
            c.get_mode_display(),
        ])

    return response


@requires_role("DISC")
def chair_show_instr(request, course_slug, case_slug):
    """
    Display instructor's case for Chair
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug,
                             offering__owner__in=Unit.sub_units(request.units))
    case = case.subclass()
    roles = ["DEPT"]
    case.ro_display = True
    has_global_role = 'UNIV' in (u.label for u in request.units)
    central_form = None
    if has_global_role:
        central_form = CaseCentralNoteForm(instance=case)

    context = {
        'course': course,
        'case': case,
        'roles': roles,
        'chair': True,
        'has_global_role': has_global_role,
        'central_form': central_form,
    }
    return render(request, "discipline/show.html", context)


@requires_global_role("DISC")
def central_updates(request, course_slug, case_slug):
    """
    Edits from Student Services
    """
    case = get_object_or_404(DisciplineCaseBase, slug=case_slug, offering__slug=course_slug)
    case = case.subclass()

    if 'unfinalize' in request.POST:
        case.unfinalize()
        l = LogEntry(userid=request.user.username,
                     description="unfinalized discipline case %s" % (case.slug,),
                     related_object=case)
        l.save()
        messages.add_message(request, messages.SUCCESS, 'Re-opened case for instructor editing.')

    elif 'addnote' in request.POST:
        form = CaseCentralNoteForm(request.POST, instance=case)
        if form.is_valid():
            form.instance.central_note_date = datetime.date.today()
            form.save()
            l = LogEntry(userid=request.user.username,
                         description="updated central note on %s" % (case.slug,),
                         related_object=case)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Updated Student Services note.')
            if form.cleaned_data['send']:
                case.send_letter(_currentuser(request), from_central=True)
                messages.add_message(request, messages.SUCCESS, 'Emailed updated incident report student and instructor.')

    return HttpResponseRedirect(reverse('discipline:chair_show_instr', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))


@requires_global_role('DISC')
def permission_admin(request):
    '''
    View to allow University-level dishonesty case admin manage department-level permissions
    '''
    if 'delete' in request.GET:
        r = get_object_or_404(Role, role__in=['DISC', 'DICC'], id=request.GET['delete'])
        # LOG EVENT#
        l = LogEntry(userid=request.user.username,
                     description=("deleted discipline role %s for %s") % (r.role, r.person.name()),
                     related_object=r.person)
        l.save()
        r.delete()

        messages.add_message(request, messages.SUCCESS, 'Deleted role for %s.' % (r.person.name(),))
        return HttpResponseRedirect(reverse('discipline:permission_admin'))

    elif 'renew' in request.GET:
        r = get_object_or_404(Role, role__in=['DISC', 'DICC'], id=request.GET['renew'])
        new_exp = datetime.date.today() + datetime.timedelta(days=365)
        r.expiry = new_exp
        r.save()
        # LOG EVENT#
        l = LogEntry(userid=request.user.username,
                     description=("renewed discipline role %s for %s") % (r.role, r.person.name()),
                     related_object=r.person)
        l.save()
        messages.add_message(request, messages.SUCCESS, 'Renewed role for %s.' % (r.person.name(),))
        return HttpResponseRedirect(reverse('discipline:permission_admin'))

    disc_roles = Role.objects_fresh.filter(role__in=['DISC', 'DICC']).select_related('person', 'unit')
    context = {
        'disc_roles': disc_roles,
    }
    return render(request, "discipline/permission_admin.html", context)


@requires_global_role('DISC')
def permission_admin_add(request):
    if request.method == 'POST':
        form = DisciplineRoleForm(request.POST)
        if form.is_valid():
            r = form.save()
            l = LogEntry(userid=request.user.username,
                  description=("added discipline role %s for %s") % (r.role, r.person.name()),
                  related_object=r)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Added role for %s.' % (r.person.name(),))
            return HttpResponseRedirect(reverse('discipline:permission_admin'))
    else:
        form = DisciplineRoleForm()

    context = {'form': form}
    return render(request, "discipline/permission_admin_add.html", context)


# Template editing views for sysadmin interface

@requires_global_role("SYSA")
def show_templates(request):
    templates = DisciplineTemplate.objects.all()
    context = {'templates': templates}
    return render(request, "discipline/show_templates.html", context)


@requires_global_role("SYSA")
def new_template(request):
    if request.method == 'POST':
        form = TemplateForm(request.POST)
        if form.is_valid():
            t = form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("create discipline template %i") % (t.id),
                  related_object=t)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Created template "%s".' % (t.label))
            return HttpResponseRedirect(reverse('sysadmin:show_templates'))
    else:
        form = TemplateForm()
    context = {'form': form}
    return render(request, "discipline/new_template.html", context)


@requires_global_role("SYSA")
def edit_template(request, template_id):
    template = get_object_or_404(DisciplineTemplate, id=template_id)
    if request.method == 'POST':
        form = TemplateForm(request.POST, instance=template)
        if form.is_valid():
            t = form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edit discipline template %i") % (t.id),
                  related_object=t)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Edited template "%s".' % (t.label))
            return HttpResponseRedirect(reverse('sysadmin:show_templates'))
    else:
        form = TemplateForm(instance=template)
    context = {'template': template, 'form': form}
    return render(request, "discipline/edit_template.html", context)


@requires_global_role("SYSA")
def delete_template(request, template_id):
    template = get_object_or_404(DisciplineTemplate, id=template_id)
    if request.method == 'POST':
        #LOG EVENT#
        l = LogEntry(userid=request.user.username,
              description=("deleted discipline template %i") % (template.id),
              related_object=template)
        l.save()
        messages.add_message(request, messages.SUCCESS, 'Deleted template "%s".' % (template.label))
        template.delete()
    return HttpResponseRedirect(reverse('sysadmin:show_templates'))
