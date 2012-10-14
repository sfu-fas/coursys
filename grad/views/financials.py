from django.contrib.auth.decorators import login_required
from courselib.auth import ForbiddenResponse
from django.shortcuts import render
from grad.models import Promise, OtherFunding, GradStatus, Scholarship, \
        GradProgramHistory, FinancialComment, STATUS_ACTIVE
from coredata.models import Semester
from ta.models import TAContract, TACourse
from ra.models import RAAppointment
import itertools, decimal
from grad.views.view import _can_view_student

get_semester = Semester.get_semester

@login_required
def financials(request, grad_slug):
    grad, _ = _can_view_student(request, grad_slug, funding=True)
    if grad is None:
        return ForbiddenResponse(request)

    current_status = GradStatus.objects.filter(student=grad, hidden=False).order_by('-start')[0]
    grad_status_qs = GradStatus.objects.filter(student=grad, hidden=False, status__in=STATUS_ACTIVE).select_related('start','end')
    scholarships_qs = Scholarship.objects.filter(student=grad, removed=False).select_related('start_semester','end_semester')
    promises_qs = Promise.objects.filter(student=grad, removed=False).select_related('start_semester','end_semester')
    other_fundings = OtherFunding.objects.filter(student=grad, removed=False).select_related('semester')
    
    contracts = TAContract.objects.filter(application__person=grad.person, status="SGN").select_related('posting__semester')
    appointments = RAAppointment.objects.filter(person=grad.person)
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
    all_semesters = itertools.ifilter(lambda x: isinstance(x, Semester), all_semesters)
    all_semesters = list(all_semesters)
    if len(all_semesters) == 0:
        all_semesters = [get_semester()]
    earliest_semester = min(all_semesters)
    latest_semester = max(all_semesters)

    semesters = []
    semesters_qs = Semester.objects.filter(start__gte=earliest_semester.start, end__lte=latest_semester.end).order_by('-start')

    # build data structure with funding for each semester
    for semester in semesters_qs:
        semester_total = decimal.Decimal(0)

        # other funding
        other_funding = other_fundings.filter(semester=semester)
        for other in other_funding:
            if other.eligible:
                semester_total += other.amount
        
        # scholarships
        semester_scholarships = scholarships_qs.filter(start_semester__name__lte=semester.name, end_semester__name__gte=semester.name)
        semester_eligible_scholarships = semester_scholarships.filter(scholarship_type__eligible=True)
        scholarships = []
        
        for ss in semester_scholarships:
            scholarships.append({'scholarship':ss, 'semester_amount':ss.amount/(ss.end_semester-ss.start_semester+1)})
        
        for semester_eligible_scholarship in semester_eligible_scholarships:
            if(semester_eligible_scholarship.start_semester != semester_eligible_scholarship.end_semester):
                semester_span = semester_eligible_scholarship.end_semester - semester_eligible_scholarship.start_semester + 1
                semester_total += semester_eligible_scholarship.amount/semester_span
            else:
                semester_total += semester_eligible_scholarship.amount

        # grad status        
        status = None
        for s in GradStatus.objects.filter(student=grad):
            if s.start <= semester and (s.end == None or semester <= s.end) :
                status = s.get_status_display()
        
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
        amount = 0
        courses = []
        for contract in contracts:
            if contract.posting.semester == semester:
                for course in TACourse.objects.filter(contract=contract):
                    amount += course.pay()
                    courses.append({'course': "%s (%s BU)" % (course.course.name(), course.bu),'amount': course.pay()})
        ta = {'courses':courses,'amount':amount}
        semester_total += amount

        # RAs
        amount = 0
        appt = []
        for appointment in appointments:
            app_start_sem = appointment.start_semester()
            app_end_sem = appointment.end_semester()
            length = appointment.semester_length()
            if app_start_sem <= semester and app_end_sem >= semester:
                sem_pay = appointment.lump_sum_pay/length
                amount += sem_pay
                appt.append({'desc':"RA for %s - %s" % (appointment.hiring_faculty.name(), appointment.project),
                             'amount':sem_pay, 'semesters': appointment.semester_length() })
        ra = {'appt':appt, 'amount':amount}        
        semester_total += amount

        # promises (ending in this semester, so we display them in the right spot)
        try:
            promise = promises_qs.get(end_semester=semester)
        except Promise.DoesNotExist:
            promise = None
        
        semester_data = {'semester':semester, 'status':status, 'scholarships': scholarships,
                         'promise': promise, 'semester_total': semester_total, 'comments': comments,
                         'ta': ta, 'ra': ra, 'other_funding': other_funding, 'program': program}
        semesters.append(semester_data)

    promises = []
    for promise in promises_qs:
        #data = promise.contributions_to()
        #total = 0
        #for sem in data:
        #    for key in data[sem]:
        #        for fund in data[sem][key]:
        #            if fund.promiseeligible:
        #                total += fund.semvalue
        #print total
        
        
        received = decimal.Decimal(0)
        for semester in semesters:
            if semester['semester'] < promise.start_semester or semester['semester'] > promise.end_semester:
                continue
            received += semester['semester_total']
        
        owing = received - promise.amount
        # minor logic for display. 
        if owing < 0:
            owing = abs(owing)
        else:
            owing = -1
        
        # annotate the semester where we're displaying the promise with relevant info
        for semester in semesters:
            if semester['semester'] == promise.end_semester:
                semester['promisereceived'] = received
                semester['promiseowing'] = owing

    # set frontend defaults
    page_title = "%s's Financial Summary" % (grad.person.first_name)
    crumb = "%s, %s" % (grad.person.last_name, grad.person.first_name)

    units = []
    try:
        units=request.units
    except:
        units = []

    context = {
               'semesters': semesters,
               'promises': promises,
               'page_title':page_title,
               'crumb':crumb,
               'grad':grad,
               'status': current_status,
               'unit': units,
               }
    return render(request, 'grad/view_financials.html', context)
