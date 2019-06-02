from django.contrib.auth.decorators import login_required
from courselib.auth import ForbiddenResponse, NotFoundResponse
from django.shortcuts import render
from grad.models import Promise, OtherFunding, GradStatus, Scholarship, \
        GradProgramHistory, FinancialComment, STATUS_ACTIVE
from coredata.models import Semester
from ta.models import TAContract, TACourse, STATUSES_NOT_TAING
from tacontracts.models import TAContract as NewTAContract
from ra.models import RAAppointment
import itertools, decimal
from grad.views.view import _can_view_student

get_semester = Semester.get_semester
STYLES = ['complete', 'compact']

@login_required
def financials(request, grad_slug, style='complete'):
    if style not in STYLES:
        return NotFoundResponse(request)

    grad, _, units = _can_view_student(request, grad_slug, funding=True)
    if grad is None:
        return ForbiddenResponse(request)

    current_status = GradStatus.objects.filter(student=grad, hidden=False).order_by('-start')[0]
    grad_status_qs = GradStatus.objects.filter(student=grad, hidden=False, status__in=STATUS_ACTIVE).select_related('start','end')
    scholarships_qs = Scholarship.objects.filter(student=grad, removed=False).select_related('start_semester','end_semester')
    promises_qs = Promise.objects.filter(student=grad, removed=False).select_related('start_semester','end_semester')
    other_fundings = OtherFunding.objects.filter(student=grad, removed=False).select_related('semester')
    
    contracts = TAContract.objects.filter(application__person=grad.person).exclude(status__in=STATUSES_NOT_TAING).select_related('posting__semester')
    other_contracts = NewTAContract.objects.filter(person=grad.person, status__in=['NEW', 'SGN'])\
                    .select_related('category')\
                    .prefetch_related('course')
    appointments = RAAppointment.objects.filter(person=grad.person, deleted=False)
    program_history = GradProgramHistory.objects.filter(student=grad).select_related('start_semester', 'program')
    financial_comments = FinancialComment.objects.filter(student=grad, removed=False).select_related('semester')
    
    # initialize earliest starting and latest ending semesters for display. 
    # Falls back on current semester if none 
    all_semesters = itertools.chain( # every semester we have info for
                      (s.start for s in grad_status_qs),
                      (s.end for s in grad_status_qs),
                      (p.start_semester for p in promises_qs),
                      (p.end_semester for p in promises_qs),
                      (s.start_semester for s in scholarships_qs),
                      (s.end_semester for s in scholarships_qs),
                      (o.semester for o in other_fundings),
                      (c.posting.semester for c in contracts),
                      (c.semester for c in financial_comments),
                      (get_semester(a.start_date) for a in appointments),
                      (get_semester(a.end_date) for a in appointments),
                      (ph.start_semester for ph in program_history),
                    )
    all_semesters = filter(lambda x: isinstance(x, Semester), all_semesters)
    all_semesters = set(all_semesters)
    if len(all_semesters) == 0:
        all_semesters = [get_semester()]
    earliest_semester = min(all_semesters)
    latest_semester = max(all_semesters)

    semesters = []
    semesters_qs = Semester.objects.filter(start__gte=earliest_semester.start, end__lte=latest_semester.end).order_by('-start')
    current_acad_year = None

    # build data structure with funding for each semester
    for semester in semesters_qs:
        semester_total = decimal.Decimal(0)

        yearpos = (semester - grad.start_semester) % 3 # position in academic year: 0 is start of a new academic year for this student
        if not current_acad_year or yearpos == 2:
            # keep this (mutable) structure that we can alias in each semester and keep running totals
            current_acad_year = {'total': 0, 'semcount': 0, 'endsem': semester}

        # other funding
        other_funding = other_fundings.filter(semester=semester)
        other_total = 0
        for other in other_funding:
            if other.eligible:
                other_total += other.amount
                semester_total += other.amount
        
        # scholarships
        semester_scholarships = scholarships_qs.filter(start_semester__name__lte=semester.name, end_semester__name__gte=semester.name)
        semester_eligible_scholarships = semester_scholarships.filter(scholarship_type__eligible=True)
        scholarships = []

        scholarship_total = 0
        for ss in semester_scholarships:
            amt = ss.amount/(ss.end_semester-ss.start_semester+1)
            scholarship_total += amt
            scholarships.append({'scholarship': ss, 'semester_amount': amt})

        for semester_eligible_scholarship in semester_eligible_scholarships:
            if(semester_eligible_scholarship.start_semester != semester_eligible_scholarship.end_semester):
                semester_span = semester_eligible_scholarship.end_semester - semester_eligible_scholarship.start_semester + 1
                semester_total += semester_eligible_scholarship.amount/semester_span
            else:
                semester_total += semester_eligible_scholarship.amount

        # grad status        
        status = None
        status_short = None
        for s in GradStatus.objects.filter(student=grad, hidden=False).order_by('start_date'):
            if s.start <= semester and (s.end == None or semester <= s.end) :
                status = s.get_status_display()
                status_short = s.get_short_status_display()
        
        # grad program
        program = None
        for ph in program_history:
            if ph.start_semester == semester:
                program = ph
        
        # financial comments
        comments = []
        for c in financial_comments:
            if c.semester == semester:
                comments.append(c)
        
        # TAs
        ta_total = 0
        courses = []
        for contract in contracts:
            if contract.posting.semester == semester:
                for course in TACourse.objects.filter(contract=contract).exclude(bu=0).select_related('course'):
                    ta_total += course.pay()
                    if contract.status == 'SGN':
                        text = "%s (%s BU)" % (course.course.name(), course.total_bu)
                    else:
                        text = "%s (%s BU, current status: %s)" \
                             % (course.course.name(), course.total_bu, contract.get_status_display().lower())
                    courses.append({'course': text,'amount': course.pay()})
        for contract in other_contracts:
            if contract.category.hiring_semester.semester == semester:
                if contract.status == 'SGN':
                    for course in contract.course.all():
                        ta_total += course.total
                        courses.append({'course': "%s (%s BU)" % (course.course.name(), course.total_bu),
                                        'amount': course.total })
                else:
                    for course in contract.course.all():
                        courses.append({'course': "%s (%s BU - $%.02f) - Draft" % (course.course.name(), course.total_bu, course.total),
                                        'amount': 0 })
        ta = {'courses':courses,'amount':ta_total}
        semester_total += ta_total

        # RAs
        ra_total = 0
        appt = []
        for appointment in appointments:
            app_start_sem = appointment.start_semester()
            app_end_sem = appointment.end_semester()
            length = appointment.semester_length()
            if app_start_sem <= semester and app_end_sem >= semester:
                sem_pay = appointment.lump_sum_pay/length
                ra_total += sem_pay
                appt.append({'desc':"RA for %s - %s" % (appointment.hiring_faculty.name(), appointment.project),
                             'amount':sem_pay, 'semesters': appointment.semester_length() })
        ra = {'appt':appt, 'amount':ra_total}
        semester_total += ra_total
        
        # promises (ending in this semester, so we display them in the right spot)
        try:
            promise = promises_qs.filter(end_semester=semester)[0]
        except IndexError:
            promise = None
        
        current_acad_year['total'] += semester_total
        current_acad_year['semcount'] += 1
        semester_data = {'semester':semester, 'status':status, 'status_short': status_short, 'scholarships': scholarships,
                         'promise': promise, 'semester_total': semester_total, 'comments': comments,
                         'ta': ta, 'ra': ra, 'other_funding': other_funding, 'program': program,
                         'other_total': other_total, 'scholarship_total': scholarship_total,
                         'ta_total': ta_total, 'ra_total': ra_total, 'acad_year': current_acad_year}
        semesters.append(semester_data)

    promises = []
    for promise in promises_qs:
        received = decimal.Decimal(0)
        for semester in semesters:
            if semester['semester'] < promise.start_semester or semester['semester'] > promise.end_semester:
                continue
            received += semester['semester_total']
        
        owing = promise.amount - received

        # annotate the semester where we're displaying the promise with relevant info
        for semester in semesters:
            if semester['semester'] == promise.end_semester:
                semester['promisereceived'] = received
                semester['promiseowing'] = owing

    totals = {'ta': 0, 'ra': 0, 'scholarship': 0, 'other': 0, 'total': 0}
    for s in semesters:
        totals['ta'] += s['ta_total']
        totals['ra'] += s['ra_total']
        totals['scholarship'] += s['scholarship_total']
        totals['other'] += s['other_total']
        totals['total'] += s['semester_total']


    context = {
               'semesters': semesters,
               'promises': promises,
               'grad':grad,
               'status': current_status,
               'unit': units,
               'totals': totals,
               }
    return render(request, 'grad/view_financials-%s.html' % (style), context)
