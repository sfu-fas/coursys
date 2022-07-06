from courselib.auth import requires_role
from django.shortcuts import render, get_object_or_404
from coredata.models import Semester
from grad.models import GradProgram, GradStudent, Scholarship, OtherFunding
from grad.views.quick_search import ACTIVE_STATUS_ORDER
from ta.models import TACourse
from tacontracts.models import TAContract
from ra.models import RAAppointment, RARequest

import decimal

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

def _build_funding_totals(semester, programs, units):
    """
    Calculate funding in each category in this semester, for students in these units.
    Returns list of programs annotated with the totals
    """
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
    total = _FakeProgram(label="Total **", pid=-2)
    programs.append(total)
    for prog in programs:
        prog.funding_ta = decimal.Decimal(0)
        prog.funding_ra = decimal.Decimal(0)
        prog.funding_schol = decimal.Decimal(0)
        prog.funding_other = decimal.Decimal(0)

    prog_lookup = dict((prog.id, prog) for prog in programs)

    # TA funding
    # - /ta
    tacourses = TACourse.objects.filter(contract__posting__semester=semester,
                                        contract__posting__unit__in=units,
                                        contract__status='SGN') \
                        .select_related('contract__application')
    for crs in tacourses:
        person_id = crs.contract.application.person_id
        if person_id in student_programs:
            prog_id = student_programs[person_id]
            prog = prog_lookup[prog_id]
        else:
            prog = non_grad
        pay = crs.pay()
        prog.funding_ta += pay
        total.funding_ta += pay
    # - /tacontracts
    tacontracts = TAContract.objects.filter(category__hiring_semester__semester=semester, category__hiring_semester__unit__in=units, status='SGN')
    for tac in tacontracts: 
        person_id = tac.person_id
        if person_id in student_programs:
            prog_id = student_programs[person_id]
            prog = prog_lookup[prog_id]
        else:
            prog = non_grad
        pay = tac.total
        prog.funding_ta += pay
        total.funding_ta += pay

    # RA funding
    # - oldra
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
        prog.funding_ra += pay
        total.funding_ra += pay
    # - newra
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
        prog.funding_ra += pay
        total.funding_ra += pay

    # scholarships
    schols = Scholarship.objects.filter(student__program__unit__in=units,
                                        start_semester__name__lte=semester.name, end_semester__name__gte=semester.name,
                                        removed=False, scholarship_type__eligible=True) \
                        .select_related('student', 'start_semester', 'end_semester')
    for sch in schols:
        prog_id = sch.student.program_id
        prog = prog_lookup[prog_id]
        length = sch.end_semester - sch.start_semester + 1
        pay = sch.amount / length
        prog.funding_schol += pay
        total.funding_schol += pay

    # other funding
    others = OtherFunding.objects.filter(student__program__unit__in=units, semester=semester, removed=False, eligible=True).select_related('student')
    for oth in others:
        prog_id = oth.student.program_id
        prog = prog_lookup[prog_id]
        pay = oth.amount
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

