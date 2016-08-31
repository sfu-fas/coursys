import copy
import datetime
import itertools
import json
import operator
import StringIO
from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_DOWN

from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, get_list_or_404, render
from django.db import transaction

from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.http import StreamingHttpResponse
from django.http import HttpResponseBadRequest
from django.core.exceptions import PermissionDenied

from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template.base import Template
from django.template.context import Context
from courselib.search import find_userid_or_emplid

from coredata.models import Person, Unit, Role, Member, CourseOffering, Semester, FuturePerson
from grad.models import Supervisor
from ra.models import RAAppointment

from faculty.models import CareerEvent, MemoTemplate, Memo, EventConfig, FacultyMemberInfo
from faculty.models import Grant, TempGrant, GrantOwner, Position
from faculty.models import EVENT_TYPES, EVENT_TYPE_CHOICES, EVENT_TAGS, ADD_TAGS
from faculty.forms import MemoTemplateForm, MemoForm, MemoFormWithUnit, AttachmentForm, TextAttachmentForm, \
    ApprovalForm, GetSalaryForm, TeachingSummaryForm, DateRangeForm
from faculty.forms import SearchForm, EventFilterForm, GrantForm, GrantImportForm, UnitFilterForm, \
    NewRoleForm, PositionForm, PositionPickerForm, PositionPersonForm, FuturePersonForm, PositionCredentialsForm
from faculty.forms import AvailableCapacityForm, CourseAccreditationForm
from faculty.forms import FacultyMemberInfoForm, TeachingCreditOverrideForm, PositionAttachmentForm
from faculty.processing import FacultySummary
from templatetags.event_display import fraction_display
from faculty.util import ReportingSemester, make_csv_writer_response
from faculty.event_types.choices import Choices
from faculty.event_types.career import AccreditationFlagEventHandler
from faculty.event_types.career import SalaryBaseEventHandler
from coredata.models import AnyPerson
from dashboard.letters import position_yellow_form_limited, position_yellow_form_tenure
from log.models import LogEntry


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


def _get_grants(units, **kwargs):
    subunit_ids = Unit.sub_unit_ids(units)
    grants = Grant.objects.active().filter(unit__id__in=subunit_ids, **kwargs)
    return grants


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
    sub_units = Unit.sub_units(request.units)
    fac_roles = Role.objects.filter(role='FAC', unit__in=sub_units).select_related('person', 'unit').order_by('person')

    fac_roles_gone = [r for r in fac_roles if r.gone]
    fac_roles_gone = itertools.groupby(fac_roles_gone, key=lambda ro: ro.person)
    fac_roles_gone = [(p, [r.unit for r in roles], CareerEvent.current_ranks(p)) for p, roles in fac_roles_gone]

    fac_roles = [r for r in fac_roles if not r.gone]
    fac_roles = itertools.groupby(fac_roles, key=lambda ro: ro.person)
    fac_roles = [(p, [r.unit for r in roles], CareerEvent.current_ranks(p)) for p, roles in fac_roles]

    editor = get_object_or_404(Person, userid=request.user.username)
    events = CareerEvent.objects.filter(status='NA').only_subunits(request.units)
    events = [e.get_handler() for e in events]
    events = [h for h in events if h.can_approve(editor)]
    filterform = UnitFilterForm(sub_units)

    future_people = FuturePerson.objects.visible()

    context = {
        'fac_roles': fac_roles,
        'fac_roles_gone': fac_roles_gone,
        'queued_events': len(events),
        'filterform': filterform,
        'viewvisas': request.GET.get('viewvisas', False),
        'future_people': future_people
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
    member_units = Unit.sub_units(request.units)
    unit_choices = [('', u'\u2012',)] + [(u.id, u.name) for u in Unit.sub_units(request.units)]
    filterform = UnitFilterForm(Unit.sub_units(request.units))

    results = []

    if request.GET:
        form = SearchForm(request.GET)
        form.fields['unit'].choices = unit_choices
        rules = Handler.get_search_rules(viewer, member_units, request.GET)

        if form.is_valid() and Handler.validate_all_search(rules):
            events = CareerEvent.objects.only_subunits(request.units).by_type(Handler).not_deleted()

            # Filter events by date
            start_date, end_date = form.cleaned_data['start_date'], form.cleaned_data['end_date']
            if start_date and end_date:
                # Events that were active during the date range
                events = events.overlaps_daterange(start_date, end_date)
            elif start_date:
                # Events since the start date
                events = events.filter(start_date__gte=start_date)
            elif end_date:
                # Events before the end date
                events = events.filter(end_date__lte=end_date)

            # Filter by unit
            if form.cleaned_data['unit']:
                events = events.filter(unit=form.cleaned_data['unit'])

            # Filter events that are still active today
            if form.cleaned_data['only_current']:
                events = events.effective_now()

            # Filter events by the Handler specific rules + viewable_by
            results = Handler.filter(events, rules=rules, viewer=viewer)
    else:
        form = SearchForm()
        form.fields['unit'].choices = unit_choices
        rules = Handler.get_search_rules(viewer, member_units)

    context = {
        'event_type': Handler.NAME,
        'form': form,
        'search_rules': rules,
        'results_columns': Handler.get_search_columns(),
        'results': results,
        'filterform': filterform,
    }
    return render(request, 'faculty/search_form.html', context)


@requires_role('ADMN')
@transaction.atomic
def manage_faculty_roles(request):
    units = Unit.sub_units(request.units)
    unit_choices = [(u.id, u.name) for u in units]
    roles = Role.objects.filter(role='FAC', unit__in=units).select_related('person', 'unit')

    if request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'add':
        # submission to create new faculty member
        form = NewRoleForm(request.POST)
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            if form.old_role:
                form.old_role.config['gone'] = False
                form.old_role.save()
            else:
                role = form.save(commit=False)
                role.role = 'FAC'
                role.save()
            messages.success(request, 'New faculty role added.')
            return HttpResponseRedirect(reverse(manage_faculty_roles))

    elif request.method == 'POST' and 'action' in request.POST and request.POST['action'] == 'del':
        # submission to delete faculty member
        form = NewRoleForm()
        form.fields['unit'].choices = unit_choices
        roleid = request.POST.get('role_id', None)
        role = get_object_or_404(Role, id=roleid)
        role.gone = True
        role.save()
        messages.success(request, 'Faculty member marked as "gone".')
        return HttpResponseRedirect(reverse(manage_faculty_roles))

    else:
        form = NewRoleForm()
        form.fields['unit'].choices = unit_choices

    context = {
        'roles': roles,
        'form': form,
    }
    return render(request, 'faculty/manage_faculty_roles.html', context)


@requires_role('ADMN')
def salary_index(request):
    """
    Salaries of all faculty members
    """
    if request.GET:
        form = GetSalaryForm(request.GET)

        if form.is_valid():
            date = form.cleaned_data['date']
        else:
            date = datetime.date.today()

    else:
        date = datetime.date.today()
        initial = {'date': date}
        form = GetSalaryForm(initial=initial)

    fac_roles_pay = _salary_index_data(request, date)

    context = {
        'form': form,
        'fac_roles_pay': fac_roles_pay,
        'date': date,
        'filterform': UnitFilterForm(Unit.sub_units(request.units)),
    }
    return render(request, 'faculty/reports/salary_index.html', context)


def _salary_index_data(request, date):
    sub_unit_ids = Unit.sub_unit_ids(request.units)
    fac_roles_pay = Role.objects.filter(role='FAC', unit__id__in=sub_unit_ids).select_related('person', 'unit')
    fac_pay_summary = []

    for role in fac_roles_pay:
        person = role.person
        unit = role.unit
        salary_events = copy.copy(FacultySummary(person).salary_events(date, units=[unit]))
        add_salary_total = add_bonus_total = 0
        salary_fraction_total = 1

        for event in salary_events:
            event.add_salary, event.salary_fraction, event.add_bonus = FacultySummary(person).salary_event_info(event)
            add_salary_total += event.add_salary
            salary_fraction_total = salary_fraction_total*event.salary_fraction
            add_bonus_total += event.add_bonus

        # get most recent step and rank from base_salary
        recent_salary_update = FacultySummary(person).recent_salary(date, units=[unit])
        if recent_salary_update is not None:
            try:
                step = recent_salary_update.config["step"]
            except KeyError:
                step = "-"
            try:
                handler = recent_salary_update.get_handler()
                rank = handler.get_display('rank')
            except KeyError:
                rank = "-"
        else:
            step = "-"
            rank = "-"

        current_salary = FacultySummary(person).salary(date, units=[unit])

        fac_pay_summary += [(person, unit, current_salary, add_salary_total, salary_fraction_total,
                             add_bonus_total, step, rank)]

    return fac_pay_summary


@requires_role('ADMN')
def salary_index_csv(request):
    if request.GET:
        form = GetSalaryForm(request.GET)
        if form.is_valid():
            date = form.cleaned_data['date']
        else:
            date = datetime.date.today()

    else:
        date = datetime.date.today()

    filename = 'salary_summary_{}.csv'.format(date.isoformat())
    csv, response = make_csv_writer_response(filename)
    csv.writerow([
        'Name',
        'Rank',
        'Step',
        'Unit',
        'Total Salary',
        'Multiplier',
        'Bonus',
        'Total Pay',
    ])

    for person, unit, pay, salary, fraction, bonus, step, rank in _salary_index_data(request, date):
        csv.writerow([
            person.name(),
            rank,
            step,
            unit.informal_name(),
            salary,
            _csvfrac(fraction),
            bonus,
            pay,
        ])

    return response


@requires_role('ADMN')
def fallout_report(request):

    if request.GET:
        form = DateRangeForm(request.GET)

        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
        else:
            today = datetime.date.today()
            start_date = datetime.date(today.year, 1, 1)
            end_date = datetime.date(today.year, 12, 31)

    else:
        end_date = datetime.date.today()
        start_date = datetime.date(end_date.year, 1, 1)
        initial = {'start_date': start_date,
                   'end_date': end_date}
        form = DateRangeForm(initial=initial)

    table = _fallout_report_data(request, start_date, end_date)

    context = {
        'form': form,
        'table': table,
        # 'tot_fallout': tot_fallout, not using this at the moment
        'start_date': start_date,
        'end_date': end_date,
        'filterform': UnitFilterForm(Unit.sub_units(request.units)),
    }
    return render(request, 'faculty/reports/fallout_report.html', context)


def _fallout_report_data(request, start_date, end_date):
    sub_unit_ids = Unit.sub_unit_ids(request.units)
    fac_roles = Role.objects.filter(role='FAC', unit__id__in=sub_unit_ids).select_related('person', 'unit')
    table = []
    tot_fallout = 0
    for role in fac_roles:
        unit = role.unit
        p = role.person
        salary = FacultySummary(p).salary(end_date, units=[unit])
        salary_events = CareerEvent.objects.approved().overlaps_daterange(start_date, end_date) \
            .filter(person=p, unit=unit, flags=CareerEvent.flags.affects_salary)
        for event in salary_events:
            if event.event_type == 'LEAVE' or event.event_type == 'STUDYLEAVE':
                days = event.get_duration_within_range(start_date, end_date)
                fraction = FacultySummary(p).salary_event_info(event)[1]
                d = fraction.denominator
                n = fraction.numerator
                fallout = Decimal((salary - salary*n/d)*days/365).quantize(Decimal('.01'), rounding=ROUND_DOWN)
                tot_fallout += fallout

                table += [(unit.label, p, event, event.start_date, event.end_date, days, salary, fraction, fallout)]
    return table


@requires_role('ADMN')
def fallout_report_csv(request):
    if request.GET:
        form = DateRangeForm(request.GET)

        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            end_date = form.cleaned_data['end_date']
        else:
            end_date = datetime.date.today()
            start_date = datetime.date(end_date.year, 1, 1)

    else:
        end_date = datetime.date.today()
        start_date = datetime.date(end_date.year, 1, 1)

    filename = 'fallout_report_{}-{}.csv'.format(start_date.isoformat(), end_date.isoformat())
    csv, response = make_csv_writer_response(filename)
    csv.writerow([
        'Unit',
        'Name',
        'Event',
        'Start',
        'End',
        'Days',
        'Salary',
        'Fraction',
        'Fallout'
    ])

    for units, p, event, start, end, days, salary, fraction, fallout in _fallout_report_data(request, start_date, end_date):
        csv.writerow([
            units,
            p.name(),
            event.get_handler().short_summary(),
            start,
            end,
            days,
            salary,
            _csvfrac(fraction),
            fallout,
        ])

    return response


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

    if request.GET:
        form = GetSalaryForm(request.GET)

        if form.is_valid():
            date = request.GET.get('date', None)
        else:
            date = datetime.date.today()

    else:
        date = datetime.date.today()
        initial = { 'date': date }
        form = GetSalaryForm(initial=initial)

    pay_tot = FacultySummary(person).salary(date, units=member_units)

    salary_events = copy.copy(FacultySummary(person).salary_events(date, units=member_units))
    add_salary_total = add_bonus_total = 0
    salary_fraction_total = 1

    for event in salary_events:
        event.add_salary, event.salary_fraction, event.add_bonus = FacultySummary(person) \
            .salary_event_info(event)
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

    return render(request, 'faculty/reports/salary_summary.html', context)


def _teaching_capacity_data(unit, semester):
    people = set(role.person for role in Role.objects.filter(role='FAC', unit=unit))

    for person in sorted(people):
        summary = FacultySummary(person)
        credits, load = summary.teaching_credits(semester, units=[unit])

        # -load: we're showing "expected teaching load"
        # -capacity: if this is negative, then we have available capacity
        yield person, credits, -load, -(credits + load)


@requires_role('ADMN')
def teaching_capacity(request):
    sub_units = Unit.sub_units(request.units)

    form = AvailableCapacityForm(request.GET)
    collected_units = []

    context = {
        'form': form,
        'units': collected_units,
        'filterform': UnitFilterForm(Unit.sub_units(request.units)),
    }

    if form.is_valid():
        start_code = form.cleaned_data['start_semester']
        end_code = form.cleaned_data['end_semester']
        context['start_code'] = start_code
        context['end_code'] = end_code

        for unit in sub_units:
            entries = []
            total_capacity = 0

            for semester in ReportingSemester.range(start_code, end_code):
                for person, credits, load, capacity in _teaching_capacity_data(unit, semester):
                    total_capacity += capacity
                    entries.append((semester, person, credits, load, capacity))

            collected_units.append((unit, entries, total_capacity))

    return render(request, 'faculty/reports/teaching_capacity.html', context)


@requires_role('ADMN')
def teaching_capacity_csv(request):
    sub_units = Unit.sub_units(request.units)

    form = AvailableCapacityForm(request.GET)

    if form.is_valid():
        start_code = form.cleaned_data['start_semester']
        end_code = form.cleaned_data['end_semester']

        filename = 'teaching_capacity_{}-{}.csv'.format(start_code, end_code)
        csv, response = make_csv_writer_response(filename)
        csv.writerow([
            'Unit',
            'Semester',
            'Person',
            'Expected teaching load',
            'Teaching credits',
            'Available capacity',
        ])

        for unit in sub_units:
            for semester in ReportingSemester.range(start_code, end_code):
                for person, credits, load, capacity in _teaching_capacity_data(unit, semester):
                    csv.writerow([
                        unit.label,
                        semester.code,
                        person.name(),
                        _csvfrac(load),
                        _csvfrac(credits),
                        _csvfrac(capacity),
                    ])

        return response

    return HttpResponseBadRequest(form.errors)


def _matched_flags(operator, selected_flags, instructor_flags):
    if operator == 'AND':
        # Instructor must have all flags
        if selected_flags <= instructor_flags:
            return selected_flags
        else:
            return None
    elif operator == 'OR':
        # Instructor must have at least one of the flags
        common = selected_flags & instructor_flags
        if common:
            return common
        else:
            return None
    elif operator == 'NONE_OF':
        # Instructor must have none of the flags
        if not selected_flags & instructor_flags:
            return instructor_flags - selected_flags
        else:
            return None
    else:
        # No filtering
        return instructor_flags


def _get_visible_flags(viewer, offering, instructor):
    return set(event.config['flag']
               for event in CareerEvent.objects.not_deleted()
                                               .by_type(AccreditationFlagEventHandler)
                                               .filter(unit=offering.owner)
                                               .filter(person=instructor)
                                               .overlaps_semester(offering.semester)
                                               .filter(status='A')
               if event.get_handler().can_view(viewer))


def _course_accreditation_data(viewer, units, semesters, operator, selected_flags):
    # Get all offerings that fall within the selected semesters.
    offerings = (CourseOffering.objects.filter(semester__in=semesters, owner__in=units)
                                       .order_by('owner', '-semester'))

    for offering in offerings:
        for instructor in offering.instructors():
            # Get flags for instructor that were active during this offering's semester
            flags = _get_visible_flags(viewer, offering, instructor)

            # Only show offering if there's a flag match
            matched_flags = _matched_flags(operator, selected_flags, flags)
            if matched_flags is not None:
                yield offering, instructor, matched_flags


@requires_role('ADMN')
def course_accreditation(request):
    viewer = get_object_or_404(Person, userid=request.user.username)
    units = Unit.sub_units(request.units)
    courses = defaultdict(list)

    # Gather all visible accreditation flags for viewer from all units
    ecs = EventConfig.objects.filter(unit__in=units,
                                     event_type=AccreditationFlagEventHandler.EVENT_TYPE)
    flag_choices = Choices(*itertools.chain(*[ec.config.get('flags', []) for ec in ecs]))

    form = CourseAccreditationForm(request.GET, flags=flag_choices)

    if form.is_valid():
        start_code = form.cleaned_data.get('start_semester')
        end_code = form.cleaned_data.get('end_semester')
        operator = form.cleaned_data.get('operator')
        selected_flags = set(form.cleaned_data.get('flag'))

        # Since CourseOfferings require actual Semesters, ignore any semesters in the
        # input range that do not "exist".
        semester_codes = [semester.code
                          for semester in ReportingSemester.range(start_code, end_code)]
        semesters = Semester.objects.filter(name__in=semester_codes)

        # Group offerings by course
        found = _course_accreditation_data(viewer, units, semesters, operator, selected_flags)
        for offering, instructor, matched_flags in found:
            presentation_flags = ((flag, flag_choices[flag]) for flag in matched_flags)
            courses[offering.course.full_name()].append((offering,
                                                         instructor,
                                                         presentation_flags))

    context = {
        'courses': dict(courses),
        'form': form,
        'filterform': UnitFilterForm(Unit.sub_units(request.units)),
        'qs': request.META['QUERY_STRING'],
    }
    return render(request, 'faculty/reports/course_accreditation.html', context)


@requires_role('ADMN')
def course_accreditation_csv(request):
    viewer = get_object_or_404(Person, userid=request.user.username)
    units = Unit.sub_units(request.units)

    # Gather all visible accreditation flags for viewer from all units
    ecs = EventConfig.objects.filter(unit__in=units,
                                     event_type=AccreditationFlagEventHandler.EVENT_TYPE)
    flag_choices = Choices(*itertools.chain(*[ec.config.get('flags', []) for ec in ecs]))

    form = CourseAccreditationForm(request.GET, flags=flag_choices)

    if form.is_valid():
        start_code = form.cleaned_data.get('start_semester')
        end_code = form.cleaned_data.get('end_semester')
        operator = form.cleaned_data.get('operator')
        selected_flags = set(form.cleaned_data.get('flag'))

        # Since CourseOfferings require actual Semesters, ignore any semesters in the
        # input range that do not "exist".
        semester_codes = [semester.code
                          for semester in ReportingSemester.range(start_code, end_code)]
        semesters = Semester.objects.filter(name__in=semester_codes)

        # Set up for CSV shenanigans
        filename = 'course_accreditation_{}-{}.csv'.format(start_code, end_code)
        csv, response = make_csv_writer_response(filename)
        csv.writerow([
            'Unit',
            'Semester',
            'Course',
            'Course Title',
            'Instructor',
            'Flags',
        ])

        found = _course_accreditation_data(viewer, units, semesters, operator, selected_flags)
        for offering, instructor, matched_flags in found:
            csv.writerow([
                offering.owner.label,
                offering.semester.name,
                offering.name(),
                offering.title,
                instructor.name(),
                ','.join(matched_flags),
            ])

        return response

    return HttpResponseBadRequest(form.errors)


@requires_role('ADMN')
def new_position(request):
    units = Unit.sub_units(request.units)
    unit_choices = [(u.id, u.name) for u in units]
    if request.method == 'POST':
        form = PositionForm(request.POST)
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            position = form.save(commit=False)
            position.config['teaching_load'] = str(form.cleaned_data.get('teaching_load'))
            position.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Position was created.'
                                 )
            l = LogEntry(userid=request.user.username,
                         description="added position: %s" % position,
                         related_object=position
                         )
            l.save()

            return HttpResponseRedirect(reverse('faculty.views.list_positions'))

    else:
        form = PositionForm()
        form.fields['unit'].choices = unit_choices

    return render(request, 'faculty/new_position.html', {'form': form})

@requires_role('ADMN')
def view_position(request, position_id):
    position = get_object_or_404(Position, pk=position_id)
    can_wizard = False
    # Let's first see if we have a real person for this position
    if position.any_person and position.any_person.person:
        person = position.any_person.get_person()
        # Then, let's see if they are a faculty member in the same unit
        if Role.objects.filter(role='FAC', unit=position.unit, person=person).exists():
            # Finally, see if they are allowed to reach the wizard, same way we do in the regular view for a
            # faculty member
            career_events = CareerEvent.objects.not_deleted().filter(person=person, unit=position.unit)
            can_wizard = not career_events.exclude(event_type='GRANTAPP').exists()

    return render(request, 'faculty/view_position.html', {'position': position, 'can_wizard': can_wizard})

@requires_role('ADMN')
def edit_position(request, position_id):
    position = get_object_or_404(Position, pk=position_id)
    if request.method == 'POST':
        form = PositionForm(request.POST, instance=position)
        if form.is_valid():
            position = form.save(commit=False)
            position.config['teaching_load'] = str(form.cleaned_data.get('teaching_load'))
            position.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Successfully edited position.'
                                 )
            l = LogEntry(userid=request.user.username,
                         description="Edited position: %s" % position,
                         related_object=position
                         )
            l.save()

            return HttpResponseRedirect(reverse('faculty.views.list_positions'))
    else:
        form = PositionForm(instance=position)
        form.fields['teaching_load'].initial = position.get_load_display()
    return render(request, 'faculty/edit_position.html', {'form': form, 'position_id': position_id})

@requires_role('ADMN')
def delete_position(request, position_id):
    position = get_object_or_404(Position, pk=position_id)
    position.hide()
    position.save()
    messages.add_message(request, messages.SUCCESS, u'Succesfully hid position.')
    l = LogEntry(userid=request.user.username, description="Hid position %s" % position, related_object=position)
    l.save()
    return HttpResponseRedirect(reverse(list_positions))


@requires_role('ADMN')
def list_positions(request):
    sub_units = Unit.sub_units(request.units)
    positions = Position.objects.visible_by_unit(sub_units)
    context = {'positions': positions}
    return render(request, 'faculty/view_positions.html', context)


@requires_role('ADMN')
def assign_position_entry(request, position_id):
    position = get_object_or_404(Position, pk=position_id)
    return render(request, 'faculty/assign_position_entry.html', {'position': position})


@requires_role('ADMN')
def assign_position_person(request, position_id):
    position = get_object_or_404(Position, pk=position_id)
    if request.method == 'POST':
        form = PositionPersonForm(request.POST)
        if form.is_valid():
            if 'person' in request.POST and request.POST['person'] is not None:
                person = form.cleaned_data['person']
                if AnyPerson.objects.filter(person=person).first():
                    any_person = AnyPerson.objects.filter(person=person).first()
                    position.any_person = any_person

                else:
                    a = AnyPerson(person=person)
                    a.save()
                    position.any_person=a
                position.save()
                # Let's see if this person already has a faculty role for this unit, otherwise, add it:
                if not Role.objects.filter(role='FAC', unit=position.unit, person=person).exists():
                    new_role = Role(role='FAC', unit=position.unit, person=person)
                    new_role.save()
                    messages.add_message(request, messages.SUCCESS, u'Added faculty role for %s' % person)
                messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Successfully assigned person to position.'
                                 )
                l = LogEntry(userid=request.user.username,
                             description="Edited position: %s" % position,
                             related_object=position
                             )
                l.save()

                return HttpResponseRedirect(reverse('faculty.views.list_positions'))

    else:
        form = PositionPersonForm()
    return render(request, 'faculty/assign_position_person.html', {'form': form, 'position_id': position_id})

@requires_role('ADMN')
def position_add_credentials(request, position_id):
    position = get_object_or_404(Position, pk=position_id)
    if request.method == 'POST':
        form = PositionCredentialsForm(request.POST, instance=position)
        if form.is_valid():
            form.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Successfully added credentials to position.'
                                 )
            l = LogEntry(userid=request.user.username,
                         description="Added credentials for position: %s" % position,
                         related_object=position
                         )
            l.save()
            return HttpResponseRedirect(reverse('faculty.views.list_positions'))
    else:
        form = PositionCredentialsForm(instance=position)
    return render(request, 'faculty/add_position_credentials.html', {'form': form, 'position': position})


@requires_role('ADMN')
def assign_position_futureperson(request, position_id):
    position = get_object_or_404(Position, pk=position_id)
    if request.method == 'POST':
        form = FuturePersonForm(request.POST)
        if form.is_valid():
            new_future_person = form.save(commit=False)
            new_future_person.set_email(form.cleaned_data.get('email'))
            new_future_person.set_gender(form.cleaned_data.get('gender'))
            new_future_person.set_sin(form.cleaned_data.get('sin'))
            new_future_person.set_birthdate(form.cleaned_data.get('birthdate'))
            new_future_person.save()
            a = AnyPerson(future_person=new_future_person)
            a.save()
            position.any_person = a
            position.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Successfully assigned person to position.'
                                 )
            l = LogEntry(userid=request.user.username,
                         description="Edited position: %s" % position,
                         related_object=position
                         )
            l.save()
            return HttpResponseRedirect(reverse('faculty.views.list_positions'))
    else:
        form = FuturePersonForm()
    return render(request, 'faculty/assign_position_futureperson.html', {'form': form, 'position_id': position_id})


def position_get_yellow_form_tenure(request, position_id):
    position = get_object_or_404(Position, pk=position_id)
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename="yellowform.pdf"'
    position_yellow_form_tenure(position, response)
    return response


def position_get_yellow_form_limited(request, position_id):
    position = get_object_or_404(Position, pk=position_id)
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename="yellowform.pdf"'
    position_yellow_form_limited(position, response)
    return response

@requires_role('ADMN')
def view_futureperson(request, futureperson_id, from_admin=0):
    """
    The from_admin parameter is used to know if we are getting here from the sysadmin panel, and only causes things
    like breadcrumbs to be different.
    """
    fp = get_object_or_404(FuturePerson, pk=futureperson_id)
    return render(request, 'faculty/view_future_person.html', {'fp': fp, 'from_admin': from_admin})



@requires_role('ADMN')
def edit_futureperson(request, futureperson_id, from_admin=0):
    """
    The from_admin parameter is used to know if we are getting here from the sysadmin panel, and only causes things
    like breadcrumbs and the page we redirect to at the end to be different.
    """
    fp = get_object_or_404(FuturePerson, pk=futureperson_id)
    if request.method == 'POST':
        form = FuturePersonForm(request.POST, instance=fp)
        if form.is_valid():
            future_person = form.save(commit=False)
            future_person.set_email(form.cleaned_data.get('email'))
            future_person.set_gender(form.cleaned_data.get('gender'))
            future_person.set_sin(form.cleaned_data.get('sin'))
            future_person.set_birthdate(form.cleaned_data.get('birthdate'))
            future_person.save()
            messages.add_message(request,
                                 messages.SUCCESS,
                                 u'Successfully edited faculty member.'
                                 )
            l = LogEntry(userid=request.user.username,
                         description="Edited future person: %s" % future_person,
                         related_object=fp
                         )
            l.save()
            if from_admin == '1':
                return HttpResponseRedirect(reverse('coredata.views.list_futurepersons'))
            else:
                return HttpResponseRedirect(reverse('faculty.views.index'))
    else:
        form = FuturePersonForm(instance=fp)
        form.fields['sin'].initial = fp.sin()
        form.fields['email'].initial = fp.email()
        form.fields['gender'].initial = fp.gender()
        form.fields['birthdate'].initial = fp.birthdate()
    return render(request, 'faculty/edit_future_person.html', {'form': form, 'fp': fp, 'from_admin': from_admin})


@requires_role('ADMN')
def delete_futureperson(request, futureperson_id):
    fp = get_object_or_404(FuturePerson, pk=futureperson_id)
    fp.hide()
    fp.save()
    messages.add_message(request, messages.SUCCESS, u'Succesfully hid future person.')
    l = LogEntry(userid=request.user.username, description="Hid future person %s" % fp, related_object=fp)
    l.save()
    return HttpResponseRedirect(reverse(index))

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
        'can_wizard': not career_events.exclude(event_type='GRANTAPP').exists(),
    }
    return render(request, 'faculty/summary.html', context)


@requires_role('ADMN')
def teaching_summary(request, userid):
    person, _ = _get_faculty_or_404(request.units, userid)

    credit_balance = 0
    events = []

    if request.GET:
        form = TeachingSummaryForm(request.GET)

        if form.is_valid():
            start = form.cleaned_data['start_semester']
            end = form.cleaned_data['end_semester']
            start_semester = ReportingSemester(start)
            end_semester = ReportingSemester(end)
        else:
            end_semester = ReportingSemester(datetime.date.today())
            start_semester = end_semester.prev().prev()

    else:
        end_semester = ReportingSemester(datetime.date.today())
        start_semester = end_semester.prev().prev()
        initial = { 'start_semester': start_semester.code,
                    'end_semester': end_semester.code }
        form = TeachingSummaryForm(initial=initial)

    curr_semester = start_semester
    while curr_semester <= end_semester:
        cb, event = _teaching_events_data(person, curr_semester)
        credit_balance += cb
        events.extend(event)
        curr_semester = curr_semester.next()

    start = start_semester.code
    end = end_semester.code
    start_label = start_semester.full_label
    end_label = end_semester.full_label

    cb_mmixed = fraction_display(credit_balance)
    context = {
        'form': form,
        'start_label': start_label,
        'end_label': end_label,
        'start_code': start,
        'end_code': end,
        'person': person,
        'credit_balance': cb_mmixed,
        'events': events,
    }
    return render(request, 'faculty/reports/teaching_summary.html', context)

def _teaching_events_data(person, semester):
    cb = 0
    e = []
    courses = Member.objects.filter(role='INST', person=person, added_reason='AUTO', offering__semester__name=semester.code) \
        .exclude(offering__component='CAN').exclude(offering__flags=CourseOffering.flags.combined) \
        .select_related('offering', 'offering__semester')
    for course in courses:
        credits, reason = course.teaching_credit_with_reason()
        enrl = '%i/%i' % (course.offering.enrl_tot, course.offering.enrl_cap)
        e += [(semester.code, course, course.offering.title, credits, reason, enrl, '')]
        cb += course.teaching_credit()

    teaching_events = FacultySummary(person).teaching_events(semester)
    for event in teaching_events:
        credits, load_decrease = FacultySummary(person).teaching_event_info(event)
        if load_decrease:
            e += [(semester.code, event.get_event_type_display(), event.get_handler().short_summary(), load_decrease, '', '', event)]
        if credits:
            e += [(semester.code, event.get_event_type_display(), event.get_handler().short_summary(), credits, '', '', event)]
        cb += credits + load_decrease

    return cb, e


@requires_role('ADMN')
def teaching_summary_csv(request, userid):
    person, _ = _get_faculty_or_404(request.units, userid)
    events = []

    if request.GET:
        form = TeachingSummaryForm(request.GET)

        if form.is_valid():
            start = form.cleaned_data['start_semester']
            end = form.cleaned_data['end_semester']
            start_semester = ReportingSemester(start)
            end_semester = ReportingSemester(end)

            curr_semester = start_semester
        else:
            end_semester = ReportingSemester(datetime.date.today())
            start_semester = end_semester.prev().prev()

    else:
        end_semester = ReportingSemester(datetime.date.today())
        start_semester = end_semester.prev().prev()

    while curr_semester <= end_semester:
        cb, event = _teaching_events_data(person, curr_semester)
        events.extend(event)
        curr_semester = curr_semester.next()

    start = start_semester.code
    end = end_semester.code

    filename = 'teaching_summary_{}-{}.csv'.format(start, end)
    csv, response = make_csv_writer_response(filename)
    csv.writerow([
        'Semester',
        'Course/Event',
        'Credits/Load Effect',
        'Credit Reason',
        'Enrollment',
        'Study Leave Calculation'
    ])

    for semester, course, summary, credits, reason, enrl, event in events:
        if event:
            if 'exclude_events' not in request.GET:
                csv.writerow([
                    semester,
                    event.get_handler().short_summary(),
                    _csvfrac(credits),
                    enrl
                ])
        else:
            csv.writerow([
                semester,
                "%s (%s)" % (course.offering.name(), summary),
                _csvfrac(credits),
                reason,
                enrl
            ])

    return response


@requires_role('ADMN')
def study_leave_credits(request, userid):
    person, units = _get_faculty_or_404(request.units, userid)
    end_semester = ReportingSemester(datetime.date.today())
    start_semester = end_semester.prev()

    if request.GET:
        form = TeachingSummaryForm(request.GET)

        if form.is_valid():
            start = form.cleaned_data['start_semester']
            end = form.cleaned_data['end_semester']
        else:
            start = start_semester.code
            end = end_semester.code

    else:
        start = start_semester.code
        end = end_semester.code
        initial = { 'start_semester': start,
                    'end_semester': end }
        form = TeachingSummaryForm(initial=initial)

    start_semester = ReportingSemester(start)
    end_semester = ReportingSemester(end)
    start_label = start_semester.full_label
    end_label = end_semester.full_label
    slc_total, events, finish_semester = _all_study_events(units, person, start_semester, end_semester)

    context = {
        'form': form,
        'start_label': start_label,
        'end_label': end_label,
        'start_code': start,
        'end_code': end,
        'person': person,
        'study_credits': fraction_display(slc_total),
        'events': events,
        'finish_semester': finish_semester.full_label,
    }
    return render(request, 'faculty/reports/study_leave_credits.html', context)


def _csvfrac(f):
    if isinstance(f, basestring):
        return f
    else:
        return "%.3f" % (f)


def _study_credit_events_data(units, person, semester, show_in_table, running_total):
    # Study credit events for one semester
    slc = 0
    e = []
    courses = Member.objects.filter(role='INST', person=person, added_reason='AUTO', offering__semester__name=semester.code) \
        .exclude(offering__component='CAN').exclude(offering__flags=CourseOffering.flags.combined) \
        .select_related('offering', 'offering__semester')
    for course in courses:
        tc = course.teaching_credit()
        running_total += tc
        if show_in_table and tc:
            e += [(semester.code, course.offering.name(), tc, tc, running_total)]

    teaching_events = FacultySummary(person).teaching_events(semester, units=units)
    for event in teaching_events:
        # only want to account for the study leave event once
        if event.event_type == 'STUDYLEAVE':
            handler = event.get_handler()
            if ReportingSemester.start_and_end_dates(semester.code)[0] <= event.start_date:
                slc = handler.get_study_leave_credits()
                running_total -= slc
                if show_in_table:
                    e += [(semester.code, 'Begin Study Leave', '', -slc , running_total)]
            if event.end_date and ReportingSemester.start_and_end_dates(semester.code)[1] >= event.end_date:
                tot = handler.get_credits_carried_forward()
                if tot != None:
                    running_total = tot
                if show_in_table:
                    e += [(semester.code, 'End Study Leave', '', '' , running_total)]
        else:
            credits, load_decrease = FacultySummary(person).teaching_event_info(event)
            running_total += credits
            if show_in_table and credits:
                    e += [(semester.code, event.get_event_type_display(), credits, credits, running_total)]

    return e, running_total

def _all_study_events(units, person, start_semester, end_semester):
    # Constructs table of study credits events for a range of semesters
    slc_total = 0
    events = []
    finish_semester = ReportingSemester(max(end_semester.code, ReportingSemester(datetime.date.today()).code)) # in case we want to look into future semesters
    curr_semester = ReportingSemester('0651')
    while curr_semester <= finish_semester:
        if start_semester <= curr_semester <= end_semester:
            event, slc_total = _study_credit_events_data(units, person, curr_semester, True, slc_total)
        else:
            event, slc_total = _study_credit_events_data(units, person, curr_semester, False, slc_total)

        if curr_semester == start_semester.prev():
            events += [('', 'Study Leave Credits prior to '+start_semester.code, '', slc_total , slc_total)]

        events += event
        curr_semester = curr_semester.next()

    return slc_total, events, finish_semester


@requires_role('ADMN')
def study_leave_credits_csv(request, userid):
    person, units = _get_faculty_or_404(request.units, userid)
    end_semester = ReportingSemester(datetime.date.today())
    start_semester = end_semester.prev()

    if request.GET:
        form = TeachingSummaryForm(request.GET)

        if form.is_valid():
            start = form.cleaned_data['start_semester']
            end = form.cleaned_data['end_semester']
        else:
            start = start_semester.code
            end = end_semester.code

    else:
        start = start_semester.code
        end = end_semester.code

    start_semester = ReportingSemester(start)
    end_semester = ReportingSemester(end)
    slc_total, events, finish_semester = _all_study_events(units, person, start_semester, end_semester)

    filename = 'study_credit_report_{}-{}.csv'.format(start, end)
    csv, response = make_csv_writer_response(filename)
    csv.writerow([
        'Semester',
        'Course/Event Type',
        'Teaching Credits',
        'Study Leave Credits',
        'Running Total',
    ])

    for semester, course, tc, slc, slc_tot in events:
        csv.writerow([
            semester,
            course,
            _csvfrac(tc),
            _csvfrac(slc),
            _csvfrac(slc_tot),
        ])

    return response


@requires_role('ADMN')
def otherinfo(request, userid):
    person, units = _get_faculty_or_404(request.units, userid)

    # collect teaching history
    instructed = Member.objects.filter(role='INST', person=person, added_reason='AUTO') \
            .exclude(offering__component='CAN').exclude(offering__flags=CourseOffering.flags.combined) \
            .select_related('offering', 'offering__semester')

    # collect grad students
    supervised = Supervisor.objects.filter(supervisor=person, supervisor_type__in=['SEN','COS','COM'], removed=False) \
            .filter(student__program__unit__in=units) \
            .select_related('student', 'student__person', 'student__program', 'student__start_semester', 'student__end_semester')

    # RA appointments supervised
    ras = RAAppointment.objects.filter(deleted=False, hiring_faculty=person, unit__in=units) \
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

    handler = instance.get_handler()

    if not handler.can_view(editor):
        raise PermissionDenied("'%s' not allowed to view this event" % editor)

    approval = None
    if handler.can_approve(editor):
        approval = ApprovalForm(instance=instance)

    context = {
        'person': person,
        'editor': editor,
        'handler': handler,
        'event': instance,
        'memos': memos,
        'templates': templates,
        'approval_form': approval,
    }
    return render(request, 'faculty/view_event.html', context)

@requires_role('ADMN')
def generate_pdf(request, userid, event_slug, pdf_key):
    """
    Generate the PDF for a given event, faculty member, and PDF type (dictated by the handler)
    """
    person, member_units = _get_faculty_or_404(request.units, userid)
    instance = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    editor = get_object_or_404(Person, userid=request.user.username)

    handler = instance.get_handler()
    if not handler.can_view(editor):
        raise PermissionDenied("'%s' not allowed to view this event" % editor)

    if pdf_key not in handler.PDFS:
        raise PermissionDenied("No such PDF for this handler")

    return handler.generate_pdf(pdf_key)

@requires_role('ADMN')
def timeline(request, userid):
    person, _ = _get_faculty_or_404(request.units, userid)
    return render(request, 'faculty/reports/timeline.html', {'person': person})


@requires_role('ADMN')
def timeline_json(request, userid):
    person, _ = _get_faculty_or_404(request.units, userid)
    viewer = get_object_or_404(Person, userid=request.user.username)

    payload = {
        'timeline': {
            'type': 'default',
            'startDate': '{:%Y,%m,%d}'.format(datetime.date.today()),
            'date': [],
            'era': [],
        },
    }
    semesters = set()

    # Populate events
    events = (CareerEvent.objects.not_deleted()
                         .only_subunits(request.units).approved()
                         .filter(person=person)
                         .exclude(event_type=SalaryBaseEventHandler.EVENT_TYPE))
    for event in events:
        handler = event.get_handler()

        if handler.can_view(viewer):
            blurb = {
                'startDate': '{:%Y,%m,%d}'.format(handler.event.start_date),
                'headline': handler.short_summary(),
                'text': u'<a href="{}">more information</a>'.format(handler.event.get_absolute_url()),
            }

            if handler.event.end_date is not None:
                payload['endDate'] = '{:%Y,%m,%d}'.format(handler.event.end_date)

            payload['timeline']['date'].append(blurb)

            # Show all semesters that the event covers, if possible.
            if event.end_date is not None:
                for semester in ReportingSemester.range(event.start_date, event.end_date):
                    semesters.add(semester)
            else:
                semesters.add(ReportingSemester(event.start_date))

    # Populate semesters
    for semester in semesters:
        payload['timeline']['era'].append({
            'startDate': '{:%Y,%m,%d}'.format(semester.start_date),
            'endDate': '{:%Y,%m,%d}'.format(semester.end_date),
            'headline': semester.short_label,
        })

    return HttpResponse(json.dumps(payload), content_type='application/json')


@requires_role('ADMN')
def faculty_member_info(request, userid):
    person, _ = _get_faculty_or_404(request.units, userid)
    info = FacultyMemberInfo.objects.filter(person=person).first()

    can_modify = True
    can_view_emergency = True

    context = {
        'person': person,
        'info': info,
        'can_modify': can_modify,
        'can_view_emergency': can_view_emergency,
    }
    return render(request, 'faculty/faculty_member_info.html', context)


@requires_role('ADMN')
@transaction.atomic
def edit_faculty_member_info(request, userid):
    person, _ = _get_faculty_or_404(request.units, userid)

    info = (FacultyMemberInfo.objects.filter(person=person).first()
            or FacultyMemberInfo(person=person))

    if request.POST:
        form = FacultyMemberInfoForm(request.POST, instance=info)

        if form.is_valid():
            new_info = form.save()
            person.set_title(new_info.title)
            person.save()
            messages.success(request, 'Contact information was saved successfully.')
            return HttpResponseRedirect(new_info.get_absolute_url())
    else:
        form = FacultyMemberInfoForm(instance=info)

    context = {
        'person': person,
        'form': form,
    }
    return render(request, 'faculty/edit_faculty_member_info.html', context)


@requires_role('ADMN')
@transaction.atomic
def teaching_credit_override(request, userid, course_slug):
    person, _ = _get_faculty_or_404(request.units, userid)
    course = get_object_or_404(Member, person=person, offering__slug=course_slug)

    context = {
        'person': person,
        'course':course,
        'course_slug': course_slug,
    }

    if request.POST:
        form = TeachingCreditOverrideForm(request.POST)
        if form.is_valid():
            course.set_teaching_credit(form.cleaned_data['teaching_credits'])
            course.set_teaching_credit_reason(form.cleaned_data['reason'])
            course.save()
            return HttpResponseRedirect(reverse(teaching_summary, kwargs={'userid':userid}))

        else:
            context.update({'form': form})
            return render(request, 'faculty/override_teaching_credit.html', context)

    else:
        credits = course.teaching_credit()
        reason = course.config.get('teaching_credit_reason', '')
        initial = { 'teaching_credits': credits,
                    'reason': reason }
        form = TeachingCreditOverrideForm(initial=initial)
        context.update({'form': form})
        return render(request, 'faculty/override_teaching_credit.html', context)


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

    Handler = _get_Handler_or_404(event_type.upper())

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
        form = Handler.get_entry_form(editor=editor, person=person, units=member_units)
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

    Handler = _get_Handler_or_404(instance.event_type)
    handler = Handler(instance)

    context = {
        'person': person,
        'editor': editor,
        'event': instance,
        'event_type': Handler.EVENT_TYPE,
    }
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
@transaction.atomic
def change_event_status(request, userid, event_slug):
    """
    Change status of event, if the editor has such privileges.
    """
    person, member_units = _get_faculty_or_404(request.units, userid)
    instance = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    editor = get_object_or_404(Person, userid=request.user.username)

    handler = instance.get_handler()
    if not handler.can_approve(editor):
        raise PermissionDenied("You cannot change status of this event")
    form = ApprovalForm(request.POST, instance=instance)
    if form.is_valid():
        event = form.save(commit=False)
        event.get_handler().save(editor)
        return HttpResponseRedirect(event.get_absolute_url())

@requires_role('ADMN')
@transaction.atomic
def faculty_wizard(request, userid, position=None):
    """
    Initial wizard for a user, set up basic events (appointment, base salary, normal teaching load).
    """
    person, member_units = _get_faculty_or_404(request.units, userid)
    editor = get_object_or_404(Person, userid=request.user.username)
    Handler_appoint = _get_Handler_or_404('APPOINT')
    Handler_salary = _get_Handler_or_404('SALARY')
    Handler_load = _get_Handler_or_404('NORM_TEACH')

    tmp1 = Handler_appoint.create_for(person)
    if not tmp1.can_edit(editor):
        raise PermissionDenied("not allowed to create events")

    context = {
        'person': person,
        'editor': editor,
        'handler': Handler_appoint,
        'name': Handler_appoint.NAME,
        'position': position
    }

    if request.method == "POST":
        form_appoint = Handler_appoint.get_entry_form(editor=editor, 
                                                      units=member_units, 
                                                      data=request.POST, 
                                                      prefix='appoint')
        form_salary = Handler_salary.get_entry_form(editor=editor, 
                                                    units=member_units, 
                                                    data=request.POST, 
                                                    prefix='salary')
        form_load = Handler_load.get_entry_form(editor=editor, 
                                                units=member_units, 
                                                data=request.POST, 
                                                prefix='load')

        # Nuke unwanted fields
        del form_appoint.fields['end_date'], form_load.fields['end_date']
        del form_salary.fields['start_date'], form_load.fields['start_date']
        del form_salary.fields['unit'], form_load.fields['unit']
        del form_appoint.fields['leaving_reason']

        if form_appoint.is_valid() and form_salary.is_valid() and form_load.is_valid():
            handler_appoint = Handler_appoint.create_for(person=person, form=form_appoint)
            handler_appoint.save(editor)
            handler_appoint.set_status(editor)

            handler_salary = Handler_salary.create_for(person=person, form=form_salary)
            handler_salary.event.start_date = handler_appoint.event.start_date
            handler_salary.event.unit = handler_appoint.event.unit
            handler_salary.save(editor)
            handler_salary.set_status(editor)

            handler_load = Handler_load.create_for(person=person, form=form_load)
            handler_load.event.start_date = handler_appoint.event.start_date
            handler_load.event.unit = handler_appoint.event.unit
            handler_load.save(editor)
            handler_load.set_status(editor)
            # Get the future faculty member from the position and set the flag that says this person's position
            # has been assigned to a real faculty member, meaning we most likely can delete this individual.
            if position:
                position = get_object_or_404(Position, pk=position)
                a = position.any_person
                a.person = person
                a.save()
                if a.future_person:
                    f = a.future_person
                    f.set_assigned(True)
                    f.save()
            return HttpResponseRedirect(reverse(summary, kwargs={'userid':userid}))
        else:
            form_list = [form_appoint, form_salary, form_load]
            context.update({"event_form": form_list})
    else:
        # Display new blank form
        form_appoint = Handler_appoint.get_entry_form(editor=editor, units=member_units, prefix='appoint')
        form_salary = Handler_salary.get_entry_form(editor=editor, units=member_units, prefix='salary')
        form_load = Handler_load.get_entry_form(editor=editor, units=member_units, prefix='load')

        # Nuke unwanted fields
        del form_appoint.fields['end_date'], form_load.fields['end_date']
        del form_salary.fields['start_date'], form_load.fields['start_date']
        del form_salary.fields['unit'], form_load.fields['unit']
        del form_appoint.fields['leaving_reason']

        # If a position was passed in from the position picker, set the initial values of the desired fields accordingly
        if position:
            position = get_object_or_404(Position, pk=position)
            form_appoint.fields['start_date'].initial = position.projected_start_date
            form_appoint.fields['unit'].initial = position.unit
            form_appoint.fields['position_number'].initial = position.position_number
            form_appoint.fields['degree1'].initial = position.degree1
            form_appoint.fields['year1'].initial = position.year1
            form_appoint.fields['location1'].initial = position.location1
            form_appoint.fields['institution1'].initial = position.institution1
            form_appoint.fields['degree2'].initial = position.degree2
            form_appoint.fields['year2'].initial = position.year2
            form_appoint.fields['location2'].initial = position.location2
            form_appoint.fields['institution2'].initial = position.institution2
            form_appoint.fields['degree3'].initial = position.degree3
            form_appoint.fields['year3'].initial = position.year3
            form_appoint.fields['location3'].initial = position.location3
            form_appoint.fields['institution3'].initial = position.institution3
            form_appoint.fields['teaching_semester_credits'].initial = position.teaching_semester_credits
            form_salary.fields['rank'].initial = position.rank
            form_salary.fields['step'].initial = position.step
            form_salary.fields['base_salary'].initial = position.base_salary
            form_salary.fields['add_salary'].initial = position.add_salary
            form_salary.fields['add_pay'].initial = position.add_pay
            form_load.fields['load'].initial = position.get_load_display()


        form_list = [form_appoint, form_salary, form_load]
        context.update({"event_form": form_list})

    return render(request, 'faculty/faculty_wizard.html', context)

@requires_role('ADMN')
def pick_position(request, userid):
    units = Unit.sub_unit_ids(request.units)
    positions = Position.objects.visible_by_unit(units)
    position_choices = [(p.id, p) for p in positions]
    person = get_object_or_404(Person, find_userid_or_emplid(userid))
    if request.method == 'POST':
        filled_form = PositionPickerForm(data=request.POST, choices=position_choices)
        if filled_form.is_valid():
            position = filled_form.cleaned_data['position_choice']
            return HttpResponseRedirect(reverse(faculty_wizard, kwargs=({'userid': userid, 'position': position})))
        else:
            return HttpResponseRedirect(reverse(faculty_wizard, kwargs=({'userid': userid})))
    else:
        new_form = PositionPickerForm(choices=position_choices)
        context = {'form': new_form, 'person': person, 'positions': position_choices}
        return render(request, 'faculty/position_picker.html', context)


###############################################################################
# Management of DocumentAttachments and Memos
@requires_role('ADMN')
@transaction.atomic
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
@transaction.atomic
def new_text_attachment(request, userid, event_slug):
    person, member_units = _get_faculty_or_404(request.units, userid)
    event = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    editor = get_object_or_404(Person, userid=request.user.username)

    form = TextAttachmentForm()
    context = {"event": event,
               "person": person,
               "form": form}

    if request.method == "POST":
        form = TextAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.career_event = event
            attachment.created_by = editor
            content = form.cleaned_data['text_contents'].encode('utf-8')
            contentio = StringIO.StringIO(content)
            contentio.size = len(content)
            attachment.contents.save('attachment.txt', contentio, save=True)
            attachment.mediatype = 'text/plain; charset=utf-8'
            attachment.save()
            return HttpResponseRedirect(event.get_absolute_url())
        else:
            context.update({"form": form})

    return render(request, 'faculty/text_attachment_form.html', context)


@requires_role('ADMN')
def view_attachment(request, userid, event_slug, attach_slug):
    person, member_units = _get_faculty_or_404(request.units, userid)
    event = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    viewer = get_object_or_404(Person, userid=request.user.username)

    attachment = get_object_or_404(event.attachments.all(), slug=attach_slug)

    handler = event.get_handler()
    if not handler.can_view(viewer):
        raise PermissionDenied("Not allowed to view this attachment")

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

    handler = event.get_handler()
    if not handler.can_view(viewer):
        raise PermissionDenied("Not allowed to download this attachment")

    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'attachment; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp

@requires_role('ADMN')
def delete_attachment(request, userid, event_slug, attach_slug):
    person, member_units = _get_faculty_or_404(request.units, userid)
    event = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    viewer = get_object_or_404(Person, userid=request.user.username)

    attachment = get_object_or_404(event.attachments.all(), slug=attach_slug)

    attachment.hide()
    messages.add_message(request,
                         messages.SUCCESS,
                         u'Attachment deleted.'
                         )
    l = LogEntry(userid=request.user.username, description="Hid attachment %s" % attachment, related_object=attachment)
    l.save()
    return HttpResponseRedirect(event.get_absolute_url())


@requires_role('ADMN')
@transaction.atomic
def new_position_attachment(request, position_id):
    position = get_object_or_404(Position, pk=position_id)
    editor = get_object_or_404(Person, userid=request.user.username)

    form = PositionAttachmentForm()
    context = {"position": position,
               "attachment_form": form}

    if request.method == "POST":
        form = PositionAttachmentForm(request.POST, request.FILES)
        if form.is_valid():
            attachment = form.save(commit=False)
            attachment.position = position
            attachment.created_by = editor
            upfile = request.FILES['contents']
            filetype = upfile.content_type
            if upfile.charset:
                filetype += "; charset=" + upfile.charset
            attachment.mediatype = filetype
            attachment.save()
            return HttpResponseRedirect(reverse(view_position, kwargs={'position_id':position.id}))
        else:
            context.update({"attachment_form": form})

    return render(request, 'faculty/position_document_attachment_form.html', context)

@requires_role('ADMN')
def view_position_attachment(request, position_id, attach_slug):
    position = get_object_or_404(Position, pk=position_id)
    attachment = get_object_or_404(position.attachments.all(), slug=attach_slug)
    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'inline; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp


@requires_role('ADMN')
def download_position_attachment(request, position_id, attach_slug):
    position = get_object_or_404(Position, pk=position_id)
    attachment = get_object_or_404(position.attachments.all(), slug=attach_slug)
    filename = attachment.contents.name.rsplit('/')[-1]
    resp = StreamingHttpResponse(attachment.contents.chunks(), content_type=attachment.mediatype)
    resp['Content-Disposition'] = 'attachment; filename="' + filename + '"'
    resp['Content-Length'] = attachment.contents.size
    return resp


@requires_role('ADMN')
def delete_position_attachment(request, position_id, attach_slug):
    position = get_object_or_404(Position, pk=position_id)
    attachment = get_object_or_404(position.attachments.all(), slug=attach_slug)
    attachment.hide()
    messages.add_message(request,
                         messages.SUCCESS,
                         u'Attachment deleted.'
                         )
    l = LogEntry(userid=request.user.username, description="Hid attachment %s" % attachment, related_object=attachment)
    l.save()
    return HttpResponseRedirect(reverse(view_position, kwargs={'position_id':position.id}))

###############################################################################
# Configuring event types, and managing memo templates


@requires_role('ADMN')
def manage_event_index(request):
    types = _get_event_types()
    context = {
        'events': types,
        }
    return render(request, 'faculty/manage_events_index.html', context)

@requires_role('ADMN')
def event_config(request, event_type):
    templates = MemoTemplate.objects.filter(unit__in=Unit.sub_units(request.units), event_type=event_type.upper(), hidden=False)
    event_type_object = next((key, Handler) for (key, Handler) in EVENT_TYPE_CHOICES if key.lower() == event_type)
    Handler = event_type_object[1]
    config_display = Handler.config_display(request.units)

    context = {
        'templates': templates,
        'event_type_slug':event_type,
        'event_name': Handler.NAME,
        'config_name': Handler.config_name,
        'config_display': config_display,
        }
    return render(request, 'faculty/event_config.html', context)

@requires_role('ADMN')
@transaction.atomic
def event_config_add(request, event_type):
    event_type_object = next((key, Handler) for (key, Handler) in EVENT_TYPE_CHOICES if key.lower() == event_type)
    Handler = _get_Handler_or_404(event_type)

    in_unit = list(request.units)[0] # pick a unit this user is in as the default owner

    if request.method == 'POST':
        form = Handler.get_config_item_form(units=request.units, data=request.POST)
        if form.is_valid():
            form.save_config()
            return HttpResponseRedirect(reverse(event_config, kwargs={'event_type':event_type}))
    else:
        form = Handler.get_config_item_form(units=request.units, initial={'unit': in_unit.id})

    context = {
        'form': form,
        'event_type_slug': event_type,
        'event_name': event_type_object[1].NAME,
        'config_name': Handler.config_name,
        }
    return render(request, 'faculty/event_config_add.html', context)

'''
@require_POST
@requires_role('ADMN')
def delete_event_flag(request, event_type, unit, flag):
    # currently not linked anywhere in frontend
    Unit.sub_units(request.units)
    unit_obj = get_object_or_404(Unit, id__in=Unit.sub_unit_ids(request.units), label=unit)
    ec, _ = EventConfig.objects.get_or_create(unit=unit_obj, event_type='FELLOW')
    list_flags = ec.config['fellowships']
    for i, (flag_short, flag_long, status) in enumerate(list_flags):
        if flag_short == flag:
            list_flags[i] = (flag_short, flag_long, 'DELETED')
            break
    ec.config['fellowships'] = list_flags
    ec.save()

    return HttpResponseRedirect(reverse(event_config, kwargs={'event_type':event_type}))
'''

@requires_role('ADMN')
def new_memo_template(request, event_type):
    person = get_object_or_404(Person, find_userid_or_emplid(request.user.username))
    unit_choices = [(u.id, u.name) for u in Unit.sub_units(request.units)]
    in_unit = list(request.units)[0] # pick a unit this user is in as the default owner
    event_type_object = next((key, Handler) for (key, Handler) in EVENT_TYPE_CHOICES if key.lower() == event_type)

    if request.method == 'POST':
        form = MemoTemplateForm(request.POST)
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = person
            f.event_type = event_type.upper()
            f.save()
            messages.success(request, "Created memo template %s for %s." % (form.instance.label, form.instance.unit))
            return HttpResponseRedirect(reverse(event_config, kwargs={'event_type':event_type}))
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
    subunits = Unit.sub_units(request.units)
    memo_template = get_object_or_404(MemoTemplate, unit__in=subunits, slug=slug)
    event_type_object = next((key, Hanlder) for (key, Hanlder) in EVENT_TYPE_CHOICES if key.lower() == event_type)
    unit_choices = [(u.id, u.name) for u in subunits]

    if request.method == 'POST':
        form = MemoTemplateForm(request.POST, instance=memo_template)
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = person
            f.event_type = event_type.upper()
            f.save()
            messages.success(request, "Updated %s template for %s." % (form.instance.label, form.instance.unit))
            return HttpResponseRedirect(reverse(event_config, kwargs={'event_type':event_type}))
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
def new_memo_no_template(request, userid, event_slug):
    person, member_units = _get_faculty_or_404(request.units, userid)
    instance = _get_event_or_404(units=member_units, slug=event_slug, person=person)
    author = get_object_or_404(Person, find_userid_or_emplid(request.user.username))
    unit_choices = [(u.id, u.name) for u in Unit.sub_units(request.units)]
    in_unit = list(request.units)[0] # pick a unit this user is in as the default owner

    ls = instance.memo_info()

    if request.method == 'POST':
        form = MemoFormWithUnit(request.POST)
        form.fields['unit'].choices = unit_choices
        if form.is_valid():
            f = form.save(commit=False)
            f.created_by = author
            f.career_event = instance
            f.config.update(ls)
            f.template = None
            f.save()
            messages.success(request, "Created new memo.")
            return HttpResponseRedirect(reverse(view_event, kwargs={'userid':userid, 'event_slug':event_slug}))
    else:
        initial = {
            'date': datetime.date.today(),
            'subject': '',
            'to_lines': person.letter_name(),
            'from_lines': '',
            'unit': in_unit,
        }
        form = MemoFormWithUnit(initial=initial)
        form.fields['unit'].choices = unit_choices

    context = {
               'form': form,
               'person': person,
               'event': instance,
               'notemplate': True,
               }
    return render(request, 'faculty/new_memo.html', context)


@requires_role('ADMN')
def new_memo(request, userid, event_slug, memo_template_slug):
    person, member_units = _get_faculty_or_404(request.units, userid)
    template = get_object_or_404(MemoTemplate, slug=memo_template_slug, unit__in=Unit.sub_units(request.units))
    instance = _get_event_or_404(units=member_units, slug=event_slug, person=person)
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
            f.template = template
            f.save()
            messages.success(request, "Created new %s memo." % (form.instance.template.label,))
            return HttpResponseRedirect(reverse(view_event, kwargs={'userid':userid, 'event_slug':event_slug}))
    else:
        initial = {
            'date': datetime.date.today(),
            'subject': '%s %s\n%s' % (person.get_title(), person.name(), template.subject),
            'to_lines': person.letter_name(),
            'from_lines': template.default_from,
            'is_letter': template.is_letter,
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

    handler = instance.get_handler()
    if not handler.can_view(person):
        return HttpResponseForbidden(request, "Not allowed to view this memo")

    if request.method == 'POST':
        form = MemoForm(request.POST, instance=memo)
        if form.is_valid():
            with transaction.atomic():
                f = form.save(commit=False)
                f.career_event = instance
                f.config['pdf_generated'] = False
                uneditable_reason = memo.uneditable_reason()
                if uneditable_reason:
                    orig_pk = f.pk
                    f.pk = None
                    f.save()
                    Memo.objects.filter(pk=orig_pk).update(hidden=True)
                    messages.success(request, "Saved new version of memo.")
                else:
                    f.save()
                    messages.success(request, "Edited memo.")
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

    handler = instance.get_handler()
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

    handler = instance.get_handler()
    if not handler.can_view(person):
        raise PermissionDenied("Not allowed to view this memo")

    context = {
               'memo': memo,
               'event': instance,
               'person': person,
               }
    return render(request, 'faculty/view_memo.html', context)

@requires_role('ADMN')
def delete_memo(request, userid, event_slug, memo_slug):
    person, member_units = _get_faculty_or_404(request.units, userid)
    instance = _get_event_or_404(units=request.units, slug=event_slug, person=person)
    memo = get_object_or_404(Memo, slug=memo_slug, career_event=instance)

    memo.hide()

    messages.add_message(request,
                         messages.SUCCESS,
                         u'Memo deleted.'
                         )
    l = LogEntry(userid=request.user.username, description="Hid memo %s" % memo, related_object=memo)
    l.save()
    return HttpResponseRedirect(instance.get_absolute_url())



###############################################################################
# Creating and editing Grants

@requires_role('ADMN')
def grant_index(request):
    editor = get_object_or_404(Person, userid=request.user.username)
    temp_grants = TempGrant.objects.filter(creator=editor)
    grants = _get_grants(request.units)
    import_form = GrantImportForm()
    context = {
        "grants": grants,
        "editor": editor,
        "temp_grants": temp_grants,
        "import_form": import_form,
    }
    return render(request, "faculty/grant_index.html", context)

@require_POST
@requires_role('ADMN')
@transaction.atomic
def import_grants(request):
    editor = get_object_or_404(Person, userid=request.user.username)
    units = Unit.sub_units(request.units)
    form = GrantImportForm(request.POST, request.FILES)
    if form.is_valid():
        csvfile = form.cleaned_data["file"]
        created, failed = TempGrant.objects.create_from_csv(csvfile, editor, units)
        if failed:
            messages.error(request, "Created %d grants, %d failed" % (len(created), len(failed)))
        else:
            messages.info(request, "Created %d grants" % (len(created)))
    return HttpResponseRedirect(reverse("grants_index"))


@requires_role('ADMN')
@transaction.atomic
def convert_grant(request, gid):
    editor = get_object_or_404(Person, userid=request.user.username)
    tmp = get_object_or_404(TempGrant, id=gid, creator=editor)
    units = Unit.sub_units(request.units)

    context = {
        "temp_grant": tmp,
        "editor": editor,
    }
    if request.method == "POST":
        form = GrantForm(units, request.POST)
        if form.is_valid():
            grant = form.save(commit=False)
            grant.label = tmp.label
            grant.project_code = tmp.project_code
            grant.save()
            GrantOwner.objects.filter(grant=grant).delete()
            for p in form.cleaned_data['owners']:
                GrantOwner(grant=grant, person=p).save()

            try:
                balance = Decimal(tmp.config["cur_balance"])
                this_month = Decimal(tmp.config["cur_month"])
                ytd_actual = Decimal(tmp.config["ytd_actual"])
                grant.update_balance(balance, this_month, ytd_actual)
            except (KeyError, InvalidOperation):
                pass
            else:
                # Delete the temporary grant
                tmp.delete()
                return HttpResponseRedirect(reverse("grants_index"))
    else:
        form = GrantForm(units, initial=tmp.grant_dict())

    context.update({"grant_form": form})
    return render(request, "faculty/convert_grant.html", context)


@require_POST
@requires_role('ADMN')
@transaction.atomic
def delete_grant(request, gid):
    editor = get_object_or_404(Person, userid=request.user.username)
    tmp = get_object_or_404(TempGrant, id=gid, creator=editor)
    tmp.delete()
    return HttpResponseRedirect(reverse("grants_index"))


#@requires_role('ADMN')
#@transaction.atomic
#def new_grant(request):
#    editor = get_object_or_404(Person, userid=request.user.username)
#    sub_unit_ids = Unit.sub_unit_ids(request.units)
#    units = Unit.objects.filter(id__in=sub_unit_ids)
#    form = GrantForm(units)
#    context = {
#        "grant_form": form,
#        "editor": editor,
#    }
#    if request.method == "POST":
#        form = GrantForm(units, request.POST)
#        if form.is_valid():
#            grant = form.save()
#            GrantOwner.objects.filter(grant=grant).delete()
#            for p in form.cleaned_data['owners']:
#                GrantOwner(grant=grant, person=p).save()
#        else:
#            context.update({"grant_form": form})
#    return render(request, "faculty/new_grant.html", context)


@requires_role('ADMN')
@transaction.atomic
def edit_grant(request, unit_slug, grant_slug):
    editor = get_object_or_404(Person, userid=request.user.username)
    units = Unit.sub_units(request.units)
    grant = get_object_or_404(Grant, unit__slug=unit_slug, slug=grant_slug, unit__in=units)

    context = {
        "grant": grant,
        "editor": editor,
    }
    if request.method == "POST":
        form = GrantForm(units, request.POST, instance=grant)
        if form.is_valid():
            grant = form.save(commit=False)
            grant.save()
            GrantOwner.objects.filter(grant=grant).delete()
            for p in form.cleaned_data['owners']:
                GrantOwner(grant=grant, person=p).save()

            return HttpResponseRedirect(reverse("view_grant", kwargs={'unit_slug': grant.unit.slug, 'grant_slug': grant.slug}))

    else:
        form = GrantForm(units, instance=grant)

    context.update({"grant_form": form})

    return render(request, "faculty/edit_grant.html", context)


@requires_role('ADMN')
def view_grant(request, unit_slug, grant_slug):
    units = Unit.sub_units(request.units)
    grant = get_object_or_404(Grant, unit__slug=unit_slug, slug=grant_slug, unit__in=units)

    context = {
        "grant": grant,
        'owners_display': grant.get_owners_display(units)
    }
    return render(request, "faculty/view_grant.html", context)
