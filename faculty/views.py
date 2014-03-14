import copy
import datetime
import itertools
import json
import operator

from courselib.auth import requires_role, NotFoundResponse
from django.shortcuts import get_object_or_404, get_list_or_404, render
from django.db import transaction
from django.db.models import Q

from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.http import StreamingHttpResponse
from django.core.exceptions import PermissionDenied

from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template.base import Template
from django.template.context import Context
from courselib.search import find_userid_or_emplid

from coredata.models import Person, Unit, Role, Member, CourseOffering, Semester
from grad.models import Supervisor
from ra.models import RAAppointment
from reports.reportlib.semester import date2semester, current_semester

from faculty.models import CareerEvent, CareerEventManager, MemoTemplate, Memo, EVENT_TYPES, EVENT_TYPE_CHOICES, EVENT_TAGS, ADD_TAGS, Grant
from faculty.forms import CareerEventForm, MemoTemplateForm, MemoForm, AttachmentForm, ApprovalForm, GetSalaryForm, TeachingSummaryForm
from faculty.forms import SearchForm, EventFilterForm, GrantForm
from faculty.processing import FacultySummary
from templatetags.event_display import fraction_display


def _get_faculty_or_404(allowed_units, userid_or_emplid):
    """
    Get the Person who has Role[role=~"faculty"] if we're allowed to see it, or raise Http404.
    """
    sub_unit_ids = Unit.sub_unit_ids(allowed_units)
    person = get_object_or_404(Person, find_userid_or_emplid(userid_or_emplid))
    roles = get_list_or_404(Role, role='FAC', unit__id__in=sub_unit_ids, person=person)
    units = set(r.unit for r in roles)
    return person, units


def _get_event_or_404(units, **kwargs):
    subunit_ids = Unit.sub_unit_ids(units)
    instance = get_object_or_404(CareerEvent, unit__id__in=subunit_ids, **kwargs)
    return instance


def _get_Handler_or_404(handler_slug):
    handler_slug = handler_slug.upper()
    if handler_slug in EVENT_TYPES:
        return EVENT_TYPES[handler_slug]
    else:
        raise Http404('Unknown event handler slug')


def _get_event_types():
    types = [{
        'slug': key.lower(),
        'name': Handler.NAME,
        'is_instant': Handler.IS_INSTANT,
        'affects_teaching': 'affects_teaching' in Handler.FLAGS,
        'affects_salary': 'affects_salary' in Handler.FLAGS
    } for key, Handler in EVENT_TYPE_CHOICES]
    return sorted(types, key=operator.itemgetter('name'))


###############################################################################
# Top-level views (management, etc. Not specific to a faculty member)

@requires_role('ADMN')
def index(request):
    sub_unit_ids = Unit.sub_unit_ids(request.units)
    fac_roles = Role.objects.filter(role='FAC', unit__id__in=sub_unit_ids).select_related('person', 'unit')
    fac_roles = itertools.groupby(fac_roles, key=lambda r: r.person)
    fac_roles = [(p, ', '.join(r.unit.informal_name() for r in roles)) for p, roles in fac_roles]

    context = {
        'fac_roles': fac_roles,
    }
    return render(request, 'faculty/index.html', context)


@requires_role('ADMN')
def search_index(request):
    editor = get_object_or_404(Person, userid=request.user.username)
    event_types = _get_event_types()
    return render(request, 'faculty/search_index.html', {
        'event_types': event_types,
        'editor': editor,
        'person': editor,
    })


@requires_role('ADMN')
def search_events(request, event_type):
    Handler = _get_Handler_or_404(event_type)
    viewer = get_object_or_404(Person, userid=request.user.username)
    unit_choices = [('', u'\u2012',)] + [(u.id, u.name) for u in Unit.sub_units(request.units)]

    results = []

    if request.GET:
        form = SearchForm(request.GET)
        form.fields['unit'].choices = unit_choices
        rules = Handler.get_search_rules(request.GET)

        if form.is_valid() and Handler.validate_all_search(rules):
            events = CareerEvent.objects.only_subunits(request.units).by_type(Handler).not_deleted()

            # TODO: Find a better place for this initial filtering logic
            if form.cleaned_data['start_date']:
                events = events.filter(start_date__gte=form.cleaned_data['start_date'])
            if form.cleaned_data['end_date']:
                events = events.filter(end_date__lte=form.cleaned_data['end_date'])
            if form.cleaned_data['unit']:
                events = events.filter(unit=form.cleaned_data['unit'])
            if form.cleaned_data['only_current']:
                events = events.effective_now()

            results = Handler.filter(events, rules=rules, viewer=viewer)
    else:
        form = SearchForm()
        form.fields['unit'].choices = unit_choices
        rules = Handler.get_search_rules()

    context = {
        'event_type': Handler.NAME,
        'form': form,
        'search_rules': rules,
        'results_columns': Handler.get_search_columns(),
        'results': results,
    }
    return render(request, 'faculty/search_form.html', context)


@requires_role('ADMN')
def salary_index(request):
    """
    Salaries of all faculty members
    """
    form = GetSalaryForm()

    if request.GET:
        form = GetSalaryForm(request.GET)

        if form.is_valid():
            date = form.cleaned_data['date']
        else:
            date = datetime.date.today()

    else:
        date = datetime.date.today()
        initial = { 'date': date }
        form = GetSalaryForm(initial=initial)

    sub_unit_ids = Unit.sub_unit_ids(request.units)
    fac_roles_pay = Role.objects.filter(role='FAC', unit__id__in=sub_unit_ids).select_related('person', 'unit')
    fac_roles_pay = itertools.groupby(fac_roles_pay, key=lambda r: r.person)
    # TODO: below line should only select pay from units the user can see
    fac_roles_pay = [(p, ', '.join(r.unit.informal_name() for r in roles), FacultySummary(p).salary(date)) for p, roles in fac_roles_pay]

    pay_tot = 0
    for p, r, pay in fac_roles_pay:
        pay_tot += pay

    context = {
        'form': form,
        'fac_roles_pay': fac_roles_pay,
        'pay_tot': pay_tot,
    }
    return render(request, 'faculty/salary_index.html', context)


@requires_role('ADMN')
def status_index(request):
    """
    Status list of for all yet-to-be approved events.
    """
    editor = get_object_or_404(Person, userid=request.user.username)
    events = CareerEvent.objects.filter(status='NA').only_subunits(request.units)
    events = [e for e in events if e.get_handler().can_view(editor)]
    context = {
        'events': events,
        'editor': editor,
    }
    return render(request, 'faculty/status_index.html', context)


@requires_role('ADMN')
def salary_summary(request, userid):
    """
    Shows all salary career events at a date
    """
    person, member_units = _get_faculty_or_404(request.units, userid)
    form = GetSalaryForm()

    if request.GET:
        form = GetSalaryForm(request.GET)

        if form.is_valid():
            date = request.GET.get('date', None)

    else:
        date = datetime.date.today()
        initial = { 'date': date }
        form = GetSalaryForm(initial=initial)

    # TODO: below code should return only salary in units user is allowed to see
    pay_tot = FacultySummary(person).salary(date)

    salary_events = copy.copy(FacultySummary(person).salary_events(date))
    add_salary_total = add_bonus_total = 0
    salary_fraction_total = 1

    for event in salary_events:
        event.add_salary, event.salary_fraction, event.add_bonus = FacultySummary(person).salary_event_info(event)
        add_salary_total += event.add_salary
        salary_fraction_total = salary_fraction_total*event.salary_fraction
        add_bonus_total += event.add_bonus

    context = {
        'form': form,
        'date': date,
        'person': person,
        'pay_tot': pay_tot,
        'salary_events': salary_events,
        'add_salary_total': add_salary_total,
        'salary_fraction_total': salary_fraction_total,
        'add_bonus_total': add_bonus_total,
    }

    return render(request, 'faculty/salary_summary.html', context)


@requires_role('ADMN')
def teaching_capacity(request):
    units = {}
    semester = Semester.current()

    for unit in Unit.objects.all():
        people = set(role.person for role in Role.objects.filter(unit=unit))
        units[unit.name] = []
        for person in people:
            summary = FacultySummary(person)
            credits, load = summary.teaching_credits(semester)
            units[unit.name].append((person, credits, load))

    return render(request, 'faculty/reports/teaching_capacity.html', {'units': units})


###############################################################################
# Display/summary views for a faculty member

@requires_role('ADMN')
def summary(request, userid):
    """
    Summary page for a faculty member.
    """
    person, _ = _get_faculty_or_404(request.units, userid)
    editor = get_object_or_404(Person, userid=request.user.username)
    career_events = CareerEvent.objects.not_deleted().only_subunits(request.units).filter(person=person)
    filterform = EventFilterForm()

    context = {
        'person': person,
        'editor': editor,
        'career_events': career_events,
        'filterform': filterform,
    }
    return render(request, 'faculty/summary.html', context)


@requires_role('ADMN')
def teaching_summary(request, userid):
    person, _ = _get_faculty_or_404(request.units, userid)
    form = TeachingSummaryForm()

    credit_balance = 0
    events = []

    def teaching_events_table(semester):
        cb = 0
        e = []
        courses = Member.objects.filter(role='INST', person=person, added_reason='AUTO', offering__semester__name=semester.name) \
            .exclude(offering__component='CAN').exclude(offering__flags=CourseOffering.flags.combined) \
            .select_related('offering', 'offering__semester')
        for course in courses:
            e += [(semester.name, course.offering.name(), course.offering.title, course.teaching_credit())]
            cb += course.teaching_credit()

        # TODO: should filter only user-visible events
        teaching_events = FacultySummary(person).teaching_events(semester)
        for event in teaching_events:
            credits, load_decrease = FacultySummary(person).teaching_event_info(event)
            if load_decrease:
                e += [(semester.name, event.get_event_type_display(), event.get_handler().short_summary(), load_decrease)]
            if credits:
                e += [(semester.name, event.get_event_type_display(), event.get_handler().short_summary(), credits)]
            cb += credits + load_decrease

        return cb, e

    if request.GET:
        form = TeachingSummaryForm(request.GET)

        if form.is_valid():
            start = form.cleaned_data['start_semester']
            end = form.cleaned_data['end_semester']
            start_semester = Semester(name=start)
            end_semester = Semester(name=end)

            curr_semester = start_semester
            while curr_semester <= end_semester:
                cb, event = teaching_events_table(curr_semester)
                credit_balance += cb
                events += event

                curr_semester = curr_semester.next_semester()

    else:
        start_semester = end_semester = Semester.current()
        start = end = start_semester.name
        initial = { 'start_semester': start,
                    'end_semester': end }
        form = TeachingSummaryForm(initial=initial)
        credit_balance, events = teaching_events_table(start_semester)

    cb_mmixed = fraction_display(credit_balance)
    context = {
        'form': form,
        'person': person,
        'credit_balance': cb_mmixed,
        'events': events,
    }
    return render(request, 'faculty/teaching_summary.html', context)


@requires_role('ADMN')
def study_leave_credits(request, userid):
    person, _ = _get_faculty_or_404(request.units, userid)
    form = TeachingSummaryForm()

    def study_credit_events_table(semester, show_in_table, running_total):
        cb = 0
        slc = 0
        e = []
        courses = Member.objects.filter(role='INST', person=person, added_reason='AUTO', offering__semester__name=semester.name) \
            .exclude(offering__component='CAN').exclude(offering__flags=CourseOffering.flags.combined) \
            .select_related('offering', 'offering__semester')
        for course in courses:
            if show_in_table:
                e += [(semester.name, course.offering.name(), course.teaching_credit(), '-', running_total)]
            cb += course.teaching_credit()

        # TODO: should filter only user-visible events
        teaching_events = FacultySummary(person).teaching_events(semester)
        for event in teaching_events:
            # only want to account for the study leave event once
            if event.event_type == 'STUDYLEAVE' and semester == Semester.get_semester(event.start_date):
                Handler = EVENT_TYPES[event.event_type]
                handler = Handler(event)
                slc = handler.get_study_leave_credits()
                running_total -= slc
                if show_in_table:
                    e += [(semester.name, event.get_event_type_display(), '-', -slc , running_total)]
            else:
                credits, load_decrease = FacultySummary(person).teaching_event_info(event)
                if show_in_table:
                    if load_decrease:
                        e += [(semester.name, event.get_event_type_display(), load_decrease, '-', running_total)]
                    if credits:
                        e += [(semester.name, event.get_event_type_display(), credits, '-', running_total)]
                cb += credits + load_decrease

        if cb >= 0 and (courses or teaching_events):
            slc = 2
            running_total += slc
            if show_in_table:
                e += [(semester.name, 'Study Leave Credits for '+semester.name, '-', slc , running_total)]

        return e, running_total

    def all_study_events(start_semester, end_semester):
        slc_total = 0
        events = []
        finish_semester = max(end_semester, Semester.current()) # in case we want to look into future semesters
        curr_semester = Semester(name='0651')
        while curr_semester <= finish_semester:
            if curr_semester >= start_semester and curr_semester <= end_semester:
                event, slc_total = study_credit_events_table(curr_semester, True, slc_total)
            else:
                event, slc_total = study_credit_events_table(curr_semester, False, slc_total)

            if curr_semester == start_semester.previous_semester():
                events += [('-', 'Study Leave Credits prior to '+start_semester.name, '-', slc_total , slc_total)]

            events += event
            curr_semester = curr_semester.next_semester()

        return slc_total, events, finish_semester

    if request.GET:
        form = TeachingSummaryForm(request.GET)

        if form.is_valid():
            start = form.cleaned_data['start_semester']
            end = form.cleaned_data['end_semester']
            start_semester = Semester(name=start)
            end_semester = Semester(name=end)

            slc_total, events, finish_semester = all_study_events(start_semester, end_semester)

    else:
        end_semester = Semester.current()
        start_semester = end_semester.previous_semester()
        start = start_semester.name
        end = end_semester.name
        initial = { 'start_semester': start,
                    'end_semester': end }
        form = TeachingSummaryForm(initial=initial)

        slc_total, events, finish_semester = all_study_events(start_semester, end_semester)

    slc_mmixed = fraction_display(slc_total)
    context = {
        'form': form,
        'person': person,
        'study_credits': slc_mmixed,
        'events': events,
        'finish_semester': finish_semester
    }
    return render(request, 'faculty/study_leave_credits.html', context)


@requires_role('ADMN')
def otherinfo(request, userid):
    person, _ = _get_faculty_or_404(request.units, userid)
    # TODO: should some or all of these be limited by request.units?

    # collect teaching history
    instructed = Member.objects.filter(role='INST', person=person, added_reason='AUTO') \
            .exclude(offering__component='CAN').exclude(offering__flags=CourseOffering.flags.combined) \
            .select_related('offering', 'offering__semester')

    # collect grad students
    supervised = Supervisor.objects.filter(supervisor=person, supervisor_type__in=['SEN','COS','COM'], removed=False) \
            .select_related('student', 'student__person', 'student__program', 'student__start_semester', 'student__end_semester')


    # RA appointments supervised
    ras = RAAppointment.objects.filter(deleted=False, hiring_faculty=person) \
            .select_related('person', 'project', 'account')

    context = {
        'person': person,
        'instructed': instructed,
        'supervised': supervised,
        'ras': ras,
    }
    return render(request, 'faculty/otherinfo.html', context)


@requires_role('ADMN')
def view_event(request, userid, event_slug):
    """
    Change existing career event for a faculty member.
    """
    person, member_units = _get_faculty_or_404(request.units, userid)
    instance = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    editor = get_object_or_404(Person, userid=request.user.username)
    memos = Memo.objects.filter(career_event=instance)
    templates = MemoTemplate.objects.filter(unit__in=Unit.sub_units(request.units), event_type=instance.event_type, hidden=False)
    
    Handler = EVENT_TYPES[instance.event_type](event=instance)

    if not Handler.can_view(editor):
        raise PermissionDenied("'%s' not allowed to view this event" % editor)

    # TODO: can editors change the status of events to something else?
    # TODO: For now just assuming editor who is allowed to approve event is also allowed to 
    # delete event, in essence change the status of the event to anything they want.
    approval = None
    if Handler.can_approve(editor):
        approval = ApprovalForm(instance=instance)

    context = {
        'person': person,
        'editor': editor,
        'handler': Handler,
        'event': instance,
        'memos': memos,
        'templates': templates,
        'approval_form': approval,
    }
    return render(request, 'faculty/view_event.html', context)


@requires_role('ADMN')
def timeline(request, userid):
    person, _ = _get_faculty_or_404(request.units, userid)
    return render(request, 'faculty/timeline.html', {'person': person})


@requires_role('ADMN')
def timeline_json(request, userid):
    person, _ = _get_faculty_or_404(request.units, userid)
    payload = {
        'timeline': {
            'type': 'default',
            'startDate': '{:%Y,%m,%d}'.format(datetime.date.today()),
            'date': [],
        },
    }

    for event in CareerEvent.objects.filter(person=person).not_deleted():
        handler = event.get_handler()
        if handler.can_view(person):
            blurb = handler.to_timeline()
            if blurb:
                payload['timeline']['date'].append(blurb)

    return HttpResponse(json.dumps(payload), mimetype='application/json')


###############################################################################
# Creation and editing of CareerEvents

@requires_role('ADMN')
def event_type_list(request, userid):
    types = _get_event_types()
    person, _ = _get_faculty_or_404(request.units, userid)
    editor = get_object_or_404(Person, userid=request.user.username)
    context = {
        'event_types': types,
        'person': person,
        'editor': editor,
    }
    return render(request, 'faculty/event_type_list.html', context)


@requires_role('ADMN')
@transaction.atomic
def create_event(request, userid, event_type):
    """
    Create new career event for a faculty member.
    """
    person, member_units = _get_faculty_or_404(request.units, userid)
    editor = get_object_or_404(Person, userid=request.user.username)
    
    try:
        Handler = EVENT_TYPES[event_type.upper()]
    except KeyError:
        return NotFoundResponse(request)

    tmp = Handler.create_for(person)
    if not tmp.can_edit(editor):
        raise PermissionDenied("'%s' not allowed to create this event" %(event_type))

    context = {
        'person': person,
        'editor': editor,
        'handler': Handler,
        'name': Handler.NAME,
        'event_type': Handler.EVENT_TYPE
    }

    if request.method == "POST":
        form = Handler.get_entry_form(editor=editor, units=member_units, data=request.POST)
        if form.is_valid():
            handler = Handler.create_for(person=person, form=form)
            handler.save(editor)
            handler.set_status(editor)
            return HttpResponseRedirect(handler.event.get_absolute_url())
        else:
            context.update({"event_form": form})
    else:
        # Display new blank form
        form = Handler.get_entry_form(editor=editor, units=member_units)
        context.update({"event_form": form})

    return render(request, 'faculty/career_event_form.html', context)


@requires_role('ADMN')
@transaction.atomic
def change_event(request, userid, event_slug):
    """
    Change existing career event for a faculty member.
    """
    person, member_units = _get_faculty_or_404(request.units, userid)
    instance = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    editor = get_object_or_404(Person, userid=request.user.username)

    Handler = EVENT_TYPES[instance.event_type]
    context = {
        'person': person,
        'editor': editor,
        'handler': Handler,
        'event': instance,
        'event_type': Handler.EVENT_TYPE
    }
    handler = Handler(instance)
    if not handler.can_edit(editor):
        return HttpResponseForbidden(request, "'%s' not allowed to edit this event" % editor)
    if request.method == "POST":
        form = Handler.get_entry_form(editor, member_units, handler=handler, data=request.POST)
        if form.is_valid():
            handler.load(form)
            handler.save(editor)
            context.update({"event": handler.event,
                            "event_form": form})
            return HttpResponseRedirect(handler.event.get_absolute_url())
        else:
            context.update({"event_form": form})

    else:
        # Display form from db instance
        form = Handler.get_entry_form(editor, member_units, handler=handler)
        context.update({"event_form": form})

    return render(request, 'faculty/career_event_form.html', context)


@require_POST
@requires_role('ADMN')
def change_event_status(request, userid, event_slug):
    """
    Change status of event, if the editor has such privileges.
    """
    person, member_units = _get_faculty_or_404(request.units, userid)
    instance = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    editor = get_object_or_404(Person, userid=request.user.username)
   
    Handler = EVENT_TYPES[instance.event_type](event=instance)
    if not Handler.can_approve(editor):
        raise PermissionDenied("You cannot change status of this event") 
    form = ApprovalForm(request.POST, instance=instance)
    if form.is_valid():
        event = form.save(commit=False)
        event.save(editor)
        return HttpResponseRedirect(event.get_absolute_url())


###############################################################################
# Management of DocumentAttachments and Memos
@requires_role('ADMN')
def new_attachment(request, userid, event_slug):
    person, member_units = _get_faculty_or_404(request.units, userid)
    event = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    editor = get_object_or_404(Person, userid=request.user.username)

    form = AttachmentForm()
    context = {"event": event,
               "person": person,
               "attachment_form": form}

    if request.method == "POST":
        form = AttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.career_event = event
            attachment.created_by = editor
            upfile = request.FILES['contents']
            filetype = upfile.content_type
            if upfile.charset:
                filetype += "; charset=" + upfile.charset
            attachment.mediatype = filetype
            attachment.save()
            return HttpResponseRedirect(event.get_absolute_url())
        else:
            context.update({"attachment_form": form})
    
    return render(request, 'faculty/document_attachment_form.html', context)


@requires_role('ADMN')
def view_attachment(request, userid, event_slug, attach_slug):
    person, member_units = _get_faculty_or_404(request.units, userid)
    event = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    viewer = get_object_or_404(Person, userid=request.user.username)

    attachment = get_object_or_404(event.attachments.all(), slug=attach_slug)

    Handler = EVENT_TYPES[event.event_type]
    handler = Handler(event)
    if not handler.can_view(viewer):
       raise PermissionDenied(" Not allowed to view this attachment")

    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'inline; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp

@requires_role('ADMN')
def download_attachment(request, userid, event_slug, attach_slug):
    person, member_units = _get_faculty_or_404(request.units, userid)
    event = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    viewer = get_object_or_404(Person, userid=request.user.username)

    attachment = get_object_or_404(event.attachments.all(), slug=attach_slug)

    Handler = EVENT_TYPES[event.event_type]
    handler = Handler(event)
    if not handler.can_view(viewer):
        raise PermissionDenied("aNot allowed to download this attachment")

    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'attachment; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp


###############################################################################
# Creating and editing Memo Templates

@requires_role('ADMN')
def manage_event_index(request):
    types = [ 
        {'slug': key.lower(), 'name': Handler.NAME, 'is_instant': Handler.IS_INSTANT,
         'affects_teaching': 'affects_teaching' in Handler.FLAGS,
         'affects_salary': 'affects_salary' in Handler.FLAGS}
        for key, Handler in EVENT_TYPE_CHOICES]

    context = {
               'events': types,          
               }
    return render(request, 'faculty/manage_events_index.html', context)

@requires_role('ADMN')
def memo_templates(request, event_type):
    templates = MemoTemplate.objects.filter(unit__in=Unit.sub_units(request.units), event_type=event_type.upper(), hidden=False)
    event_type_object = next((key, Hanlder) for (key, Hanlder) in EVENT_TYPE_CHOICES if key.lower() == event_type)

    context = {
               'templates': templates,
               'event_type_slug':event_type,
               'event_name': event_type_object[1].NAME        
               }
    return render(request, 'faculty/memo_templates.html', context)

@requires_role('ADMN')
def new_memo_template(request, event_type):
    person = get_object_or_404(Person, find_userid_or_emplid(request.user.username))   
    unit_choices = [(u.id, u.name) for u in Unit.sub_units(request.units)]
    in_unit = list(request.units)[0] # pick a unit this user is in as the default owner
    event_type_object = next((key, Hanlder) for (key, Hanlder) in EVENT_TYPE_CHOICES if key.lower() == event_type)

    if request.method == 'POST':
        form = MemoTemplateForm(request.POST)
        form.fields['unit'].choices = unit_choices 
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = person  
            f.event_type = event_type.upper()         
            f.save()
            messages.success(request, "Created memo template %s for %s." % (form.instance.label, form.instance.unit))
            return HttpResponseRedirect(reverse(memo_templates, kwargs={'event_type':event_type}))
    else:
        form = MemoTemplateForm(initial={'unit': in_unit})
        form.fields['unit'].choices = unit_choices

    tags = sorted(EVENT_TAGS.iteritems())
    event_handler = event_type_object[1].CONFIG_FIELDS
    #get additional tags for specific event
    add_tags = {}
    for tag in event_handler:
        try:
            add_tags[tag] = ADD_TAGS[tag]
        except KeyError:
            add_tags[tag] = tag.replace("_", " ")

    add = sorted(add_tags.iteritems())
    lt = tags + add

    context = {
               'form': form,
               'event_type_slug': event_type,
               'EVENT_TAGS': lt,
               'event_name': event_type_object[1].NAME
               }
    return render(request, 'faculty/memo_template_form.html', context)

@requires_role('ADMN')
def manage_memo_template(request, event_type, slug):
    person = get_object_or_404(Person, find_userid_or_emplid(request.user.username))   
    unit_choices = [(u.id, u.name) for u in Unit.sub_units(request.units)]
    memo_template = get_object_or_404(MemoTemplate, slug=slug)
    event_type_object = next((key, Hanlder) for (key, Hanlder) in EVENT_TYPE_CHOICES if key.lower() == event_type)

    if request.method == 'POST':
        form = MemoTemplateForm(request.POST, instance=memo_template)
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = person
            f.event_type = event_type.upper()             
            f.save()
            messages.success(request, "Updated %s template for %s." % (form.instance.label, form.instance.unit))
            return HttpResponseRedirect(reverse(memo_templates, kwargs={'event_type':event_type}))
    else:
        form = MemoTemplateForm(instance=memo_template)
        form.fields['unit'].choices = unit_choices 

    tags = sorted(EVENT_TAGS.iteritems())
    event_handler = event_type_object[1].CONFIG_FIELDS
    #get additional tags for specific event
    add_tags = {}
    for tag in event_handler:
        try:
            add_tags[tag] = ADD_TAGS[tag]
        except KeyError:
            add_tags[tag] = tag.replace("_", " ")

    add = sorted(add_tags.iteritems())
    lt = tags + add
    
    context = {
               'form': form,
               'memo_template': memo_template,
               'event_type_slug':event_type,
               'EVENT_TAGS': lt,
               'event_name': event_type_object[1].NAME
               }
    return render(request, 'faculty/memo_template_form.html', context)

###############################################################################
# Creating and editing Memos

@requires_role('ADMN')
def new_memo(request, userid, event_slug, memo_template_slug):
    person, member_units = _get_faculty_or_404(request.units, userid)
    template = get_object_or_404(MemoTemplate, slug=memo_template_slug, unit__in=member_units)
    instance = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    author = get_object_or_404(Person, find_userid_or_emplid(request.user.username))

    ls = instance.memo_info()

    if request.method == 'POST':
        form = MemoForm(request.POST)
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = author
            f.career_event = instance
            f.unit = template.unit
            f.config.update(ls)
            f.template = template;
            f.save()
            messages.success(request, "Created new %s memo for %s." % (form.instance.template.label, form.instance.career_event.title))            
            return HttpResponseRedirect(reverse(view_event, kwargs={'userid':userid, 'event_slug':event_slug}))  
    else:
        initial = {
            'date': datetime.date.today(),
            'subject': '%s %s\n%s ' % (person.get_title(), person.name(), template.subject),
            'to_lines': person.letter_name()
        }
        form = MemoForm(initial=initial)

    context = {
               'form': form,
               'template' : template,
               'person': person,
               'event': instance,
               }
    return render(request, 'faculty/new_memo.html', context)

@requires_role('ADMN')
def manage_memo(request, userid, event_slug, memo_slug):
    person, member_units = _get_faculty_or_404(request.units, userid)
    instance = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    memo = get_object_or_404(Memo, slug=memo_slug, career_event=instance)

    Handler = EVENT_TYPES[instance.event_type]
    handler = Handler(instance)
    if not handler.can_view(person):
        return HttpResponseForbidden(request, "Not allowed to view this memo")

    if request.method == 'POST':
        form = MemoForm(request.POST, instance=memo)
        if form.is_valid():
            f = form.save(commit=False)
            f.career_event = instance
            f.save()
            messages.success(request, "Updated memo for %s" % (form.instance.career_event.title))            
            return HttpResponseRedirect(reverse(view_event, kwargs={'userid':userid, 'event_slug':event_slug}))  
    else:
        form = MemoForm(instance=memo)
        
    context = {
               'form': form,
               'person': person,
               'event': instance,
               'memo': memo,
               }
    return render(request, 'faculty/manage_memo.html', context)

@requires_role('ADMN')
def get_memo_text(request, userid, event_slug, memo_template_id):
    """ Get the text from memo template """
    person, member_units = _get_faculty_or_404(request.units, userid)
    event = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    lt = get_object_or_404(MemoTemplate, id=memo_template_id, unit__in=Unit.sub_units(request.units))
    temp = Template(lt.template_text)
    ls = event.memo_info()
    text = temp.render(Context(ls))

    return HttpResponse(text, content_type='text/plain')

@requires_role('ADMN')
def get_memo_pdf(request, userid, event_slug, memo_slug):
    person, member_units = _get_faculty_or_404(request.units, userid)
    instance = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    memo = get_object_or_404(Memo, slug=memo_slug, career_event=instance)

    Handler = EVENT_TYPES[instance.event_type]
    handler = Handler(instance)
    if not handler.can_view(person):
        raise PermissionDenied("Not allowed to view this memo")

    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename="%s.pdf"' % (memo_slug)

    memo.write_pdf(response) 
    return response

@requires_role('ADMN')
def view_memo(request, userid, event_slug, memo_slug):
    person, member_units = _get_faculty_or_404(request.units, userid)
    instance = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    memo = get_object_or_404(Memo, slug=memo_slug, career_event=instance)

    Handler = EVENT_TYPES[instance.event_type]
    handler = Handler(instance)
    if not handler.can_view(person):
        raise PermissionDenied("Not allowed to view this memo")

    context = {
               'memo': memo,
               'event': instance,
               'person': person,
               }
    return render(request, 'faculty/view_memo.html', context)


###############################################################################
# Creating and editing Grants

@requires_role('ADMN')
def grant_index(request):
    grants = Grant.objects.active()
    editor = get_object_or_404(Person, userid=request.user.username)
    context = {
        "grants": grants,
        "editor": editor,
    }
    return render(request, "faculty/grant_index.html", context)

@requires_role('ADMN')
def new_grant(request):
    editor = get_object_or_404(Person, userid=request.user.username)
    sub_unit_ids = Unit.sub_unit_ids(request.units)
    units = Unit.objects.filter(id__in=sub_unit_ids)
    form = GrantForm(units)
    context = {
        "grant_form": form,
        "editor": editor,
    }
    if request.method == "POST":
        form = GrantForm(member_units, request.POST)
        if form.is_valid():
            grant = form.save(commit=False)
            grant.save()
        else:
            context.update({"grant_form": form})
    return render(request, "faculty/new_grant.html", context)
    
@requires_role('ADMN')
def view_grant(request, unit_slug, grant_slug):
    grant = get_object_or_404(Grant, unit__slug=unit_slug, slug=grant_slug)
    context = {
        "grant": grant,
    }
    return render(request, "faculty/view_grant.html", context)
