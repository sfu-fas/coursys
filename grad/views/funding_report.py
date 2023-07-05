from courselib.auth import requires_role
from django.shortcuts import render, get_object_or_404
from coredata.models import Semester
from grad.models import GradProgram, GradStudent, Scholarship, OtherFunding
from grad.views.quick_search import ACTIVE_STATUS_ORDER
from ta.models import TACourse
from tacontracts.models import TAContract
from ra.models import RAAppointment, RARequest

from django.http import HttpResponse
import decimal, csv

def __startsem_name(gs):
    if gs.start_semester:
        return gs.start_semester.name
    else:
        return '0000'

class _FakeProgram(object):
    # just enough like a GradProgram to display other totals
    def __init__(self, label, pid):
        self.label = label
        self.id = pid

def _funding_ra_old(units, semester, prog_lookup, student_programs, non_grad):
    funding = []
    sem_st, sem_en = RAAppointment.start_end_dates(semester)
    raappt = RAAppointment.objects.filter(unit__in=units, deleted=False, end_date__gte=sem_st, start_date__lte=sem_en)
    for ra in raappt:
        person_id = ra.person_id
        if person_id in student_programs:
            prog_id = student_programs[person_id]
            prog = prog_lookup[prog_id]
        else:
            prog = non_grad
        semlen = ra.semester_length()
        if semlen == 0:
            semlen = 1
        pay = ra.lump_sum_pay/semlen
        funding.append((ra, prog, pay, semlen))
    return funding

def _funding_ra_new(units, semester, prog_lookup, student_programs, non_grad):
    funding = []
    sem_st, sem_en = RARequest.start_end_dates(semester)
    reqs = RARequest.objects.filter(unit__in=units, deleted=False, complete=True, draft=False, end_date__gte=sem_st, start_date__lte=sem_en)
    for ra in reqs:
        person_id = ra.person_id
        if person_id in student_programs:
            prog_id = student_programs[person_id]
            prog = prog_lookup[prog_id]
        else:
            prog = non_grad
        semlen = ra.semester_length()
        if semlen == 0:
            semlen = 1
        pay = ra.total_pay/semlen
        funding.append((ra, prog, pay, semlen))
    return funding

def _funding_ta(units, semester, prog_lookup, student_programs, non_grad):
    funding = []
    tacourses = TACourse.objects.filter(contract__posting__semester=semester,
                                        contract__posting__unit__in=units,
                                        contract__status__in=['ACC', 'SGN']) \
                        .select_related('contract__application')
    for crs in tacourses:
        person_id = crs.contract.application.person_id
        if person_id in student_programs:
            prog_id = student_programs[person_id]
            prog = prog_lookup[prog_id]
        else:
            prog = non_grad
        pay = crs.pay()
        funding.append((crs, prog, pay))
    return funding

def _funding_tacontracts(units, semester, prog_lookup, student_programs, non_grad):
    funding = []
    tacontracts = TAContract.objects.filter(category__hiring_semester__semester=semester, category__hiring_semester__unit__in=units, status='SGN')
    for tac in tacontracts: 
        person_id = tac.person_id
        if person_id in student_programs:
            prog_id = student_programs[person_id]
            prog = prog_lookup[prog_id]
        else:
            prog = non_grad
        pay = tac.total
        funding.append((tac, prog, pay))
    return funding

def _funding_schol(units, semester, prog_lookup):
    funding = []
    schols = Scholarship.objects.filter(student__program__unit__in=units,
                                            start_semester__name__lte=semester.name, end_semester__name__gte=semester.name,
                                            removed=False, scholarship_type__eligible=True) \
                            .select_related('student', 'start_semester', 'end_semester')
    for sch in schols:
        prog_id = sch.student.program_id
        prog = prog_lookup[prog_id]
        length = sch.end_semester - sch.start_semester + 1
        pay = sch.amount / length
        funding.append((sch, prog, pay, length))
    return funding

def _funding_other(units, semester, prog_lookup):
    funding = []
    others = OtherFunding.objects.filter(student__program__unit__in=units, semester=semester, removed=False, eligible=True).select_related('student')
    for oth in others:
        prog_id = oth.student.program_id
        prog = prog_lookup[prog_id]
        pay = oth.amount
        funding.append((oth, prog, pay))
    return funding

def _build_grad_mapping(programs, units):
    # build mapping of Person.id to most-likely-currently-interesting GradProgram they're in
    gradstudents = GradStudent.objects.filter(program__unit__in=units).select_related('start_semester', 'person')
    gradstudents = list(gradstudents)
    gradstudents.sort(key=lambda gs: (-ACTIVE_STATUS_ORDER[gs.current_status], __startsem_name(gs)))
    student_programs = {}
    for gs in gradstudents:
        student_programs[gs.person_id] = gs.program_id
    del gradstudents

    programs = list(programs)
    non_grad = _FakeProgram(label="Non Grad *", pid=-1)
    programs.append(non_grad)
    prog_lookup = dict((prog.id, prog) for prog in programs)

    return prog_lookup, student_programs, non_grad, programs

def _build_funding_totals(semester, programs, units):
    """
    Calculate funding in each category in this semester, for students in these units.
    Returns list of programs annotated with the totals
    """
    prog_lookup, student_programs, non_grad, programs = _build_grad_mapping(programs, units)
    total = _FakeProgram(label="Total **", pid=-2)
    programs.append(total)
    for prog in programs:
        prog.funding_ta = decimal.Decimal(0)
        prog.funding_ra = decimal.Decimal(0)
        prog.funding_schol = decimal.Decimal(0)
        prog.funding_other = decimal.Decimal(0)

    # - ta: /ta
    funding_ta = _funding_ta(units, semester, prog_lookup, student_programs, non_grad)
    for ta in funding_ta:    
        prog, pay = ta[1], ta[2]
        prog.funding_ta += pay
        total.funding_ta += pay
    # - ta: /tacontracts
    funding_tacontracts = _funding_tacontracts(units, semester, prog_lookup, student_programs, non_grad)
    for ta in funding_tacontracts:    
        prog, pay = ta[1], ta[2]
        prog.funding_ta += pay
        total.funding_ta += pay

    # - ra: old
    funding_ra_old = _funding_ra_old(units, semester, prog_lookup, student_programs, non_grad)
    for ra_old in funding_ra_old:
        prog, pay = ra_old[1], ra_old[2]
        prog.funding_ra += pay
        total.funding_ra += pay
    # - ra: new
    funding_ra_new = _funding_ra_new(units, semester, prog_lookup, student_programs, non_grad)
    for ra_new in funding_ra_new:
        prog, pay = ra_new[1], ra_new[2]
        prog.funding_ra += pay
        total.funding_ra += pay

    # scholarships
    funding_schol = _funding_schol(units, semester, prog_lookup)
    for sch in funding_schol:
        prog, pay = sch[1], sch[2]
        prog.funding_schol += pay
        total.funding_schol += pay

    # other funding
    funding_other = _funding_other(units, semester, prog_lookup)
    for oth in funding_other:
        prog, pay = oth[1], oth[2]
        prog.funding_other += pay
        total.funding_other += pay

    return programs


@requires_role("GRAD", get_only=["GRPD"])
def funding_report(request, semester_name=None):
    if semester_name is None:
        semester = Semester.next_starting()
    else:
        semester = get_object_or_404(Semester, name=semester_name)

    programs = GradProgram.objects.filter(unit__in=request.units, hidden=False).order_by('label')
    programs = _build_funding_totals(semester, programs, request.units)
    multiple_units = False
    if len(request.units) > 1:
        multiple_units = True

    these_units = ', '.join(u.name for u in request.units)
    context = {'semester': semester, 'programs': programs, 'these_units': these_units, 'multiple_units': multiple_units}

    return render(request, 'grad/funding_report.html', context)


def _build_funding_csv(semester, programs, units, type):
    """
    List all students in these units contributing to funding for a category.
    Returns a csv response
    """
    prog_lookup, student_programs, non_grad, programs = _build_grad_mapping(programs, units)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'inline; filename="funding-report-%s-%s.csv"' % (semester.name, type)

    writer = csv.writer(response)
    if type == 'ras':
        writer.writerow(['Unit', 'Name', 'ID', 'Program', 'Supervisor', 'Start Date', 'End Date', 'Total Appointment Pay', 'Length (In Semesters)', str(semester) + " Pay", "URL"])
        # old
        funding_ra_old = _funding_ra_old(units, semester, prog_lookup, student_programs, non_grad)
        for ra in funding_ra_old:
            funding, prog, pay, semlen = ra[0], ra[1], ra[2], ra[3]
            writer.writerow([funding.unit.label, funding.person.sortname(), funding.person.emplid, prog.label, funding.hiring_faculty.sortname(), funding.start_date, funding.end_date, funding.lump_sum_pay, semlen, "{:.2f}".format(pay), funding.get_absolute_url()]) 
        # new
        funding_ra_new = _funding_ra_new(units, semester, prog_lookup, student_programs, non_grad)
        for ra in funding_ra_new:
            funding, prog, pay, semlen = ra[0], ra[1], ra[2], ra[3]
            writer.writerow([funding.unit.label, funding.get_sort_name(), funding.get_id(), prog.label, funding.supervisor.sortname(), funding.start_date, funding.end_date, funding.total_pay, semlen, "{:.2f}".format(pay), funding.get_absolute_url()])
    elif type == 'tas':
        # - /ta
        writer.writerow(['Unit', 'Name', 'ID', 'Program', str(semester) + " Pay"])
        funding_ta = _funding_ta(units, semester, prog_lookup, student_programs, non_grad)
        for crs in funding_ta:
            funding, prog, pay = crs[0], crs[1], crs[2]
            writer.writerow([funding.contract.posting.unit.label, funding.contract.application.person.sortname(), funding.contract.application.person.emplid, prog.label, "{:.2f}".format(pay)])
        # - /tacontracts
        funding_tacontracts = _funding_tacontracts(units, semester, prog_lookup, student_programs, non_grad)
        for tac in funding_tacontracts: 
            funding, prog, pay = tac[0], tac[1], tac[2]
            writer.writerow([funding.category.hiring_semester.unit.label, funding.person.sortname(), funding.person.emplid, prog.label, "{:.2f}".format(pay), "!"])
    elif type == 'scholarships':
        writer.writerow(['Unit', 'Name', 'ID', 'Program', 'Total Pay', 'Length (In Semesters)', str(semester) + " Pay"])
        funding_schol = _funding_schol(units, semester, prog_lookup)
        for sch in funding_schol:
            funding, prog, pay, length = sch[0], sch[1], sch[2], sch[3]
            writer.writerow([funding.student.program.unit.label, funding.student.person.sortname(), funding.student.person.emplid, prog.label, funding.amount, length, "{:.2f}".format(pay)])
    elif type == 'other':
        writer.writerow(['Unit', 'Name', 'ID', 'Program', str(semester) + " Pay"])
        funding_other = _funding_other(units, semester, prog_lookup)
        for oth in funding_other:
            funding, prog, pay = oth[0], oth[1], oth[2]
            writer.writerow([funding.student.program.unit.label, funding.student.person.sortname(), funding.student.person.emplid, prog.label, pay])
        
    return response


@requires_role("GRAD", get_only=["GRPD"])
def funding_report_download(request, semester_name=None, type=None):
    if semester_name is None:
        semester = Semester.next_starting()
    else:
        semester = get_object_or_404(Semester, name=semester_name)

    programs = GradProgram.objects.filter(unit__in=request.units, hidden=False).order_by('label')

    response = _build_funding_csv(semester, programs, request.units, type)
    
    return response