from django.contrib.auth.decorators import login_required
from courselib.auth import ForbiddenResponse
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, Supervisor, Promise, OtherFunding, GradStatus, Scholarship, STATUS_ACTIVE
from coredata.models import Role, Semester
from ta.models import TAContract, TACourse
from ra.models import RAAppointment
import itertools, decimal


get_semester = Semester.get_semester

@login_required
def financials(request, grad_slug):
    curr_user = request.user
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    is_student = curr_user.username == grad.person.userid    
    is_supervisor = Supervisor.objects.filter(student=grad, supervisor__userid=curr_user.username,
                                              supervisor_type='SEN', removed=False).count() > 0
    is_admin = Role.objects.filter(role='GRAD', unit=grad.program.unit, person__userid=curr_user.username).count()>0
    
    if not (is_student or is_supervisor or is_admin):
        return ForbiddenResponse(request, 'You do not have sufficient permission to access this page') 

    current_status = GradStatus.objects.filter(student=grad, hidden=False).order_by('-start')[0]
    grad_status_qs = GradStatus.objects.filter(student=grad, status__in=STATUS_ACTIVE).select_related('start','end')
    scholarships_qs = Scholarship.objects.filter(student=grad).select_related('start_semester','end_semester')
    promises_qs = Promise.objects.filter(student=grad).select_related('start_semester','end_semester')
    other_fundings = OtherFunding.objects.filter(student=grad).select_related('semester')
    
    contracts = TAContract.objects.filter(application__person=grad.person, status="SGN").select_related('posting__semester')
    appointments = RAAppointment.objects.filter(person=grad.person)
    
    # initialize earliest starting and latest ending semesters for display. 
    # Falls back on current semester if none 
    all_semesters = itertools.chain( # every semester we have info for
                      #[get_semester()],
                      (s.start for s in grad_status_qs),
                      (s.end for s in grad_status_qs),
                      (p.start_semester for p in promises_qs),
                      (p.end_semester for p in promises_qs),
                      (s.start_semester for s in scholarships_qs),
                      (s.end_semester for s in scholarships_qs),
                      (o.semester for o in other_fundings),
                      (c.posting.semester for c in contracts),
                      (get_semester(a.start_date) for a in appointments),
                      (get_semester(a.end_date) for a in appointments),
                    )
    all_semesters = itertools.ifilter(lambda x: isinstance(x, Semester), all_semesters)
    all_semesters = list(all_semesters)
    earliest_semester = min(all_semesters)
    latest_semester = max(all_semesters)

    semesters = []
    semesters_qs = Semester.objects.filter(start__gte=earliest_semester.start, end__lte=latest_semester.end).order_by('-start')

    # build data structure with funding for each semester
    for semester in semesters_qs:
        semester_total = decimal.Decimal(0)
        funding_in_semester = {}

        # other funding
        semester_other_fundings = other_fundings.filter(semester=semester)
        funding_in_semester['other_funding'] = semester_other_fundings
        
        # scholarships
        semester_scholarships = scholarships_qs.filter(start_semester__lte=semester, end_semester__gte=semester)
        semester_eligible_scholarships = semester_scholarships.filter(scholarship_type__eligible=True)
        s = []
        for ss in semester_scholarships:
            s.append({'scholarship':ss, 'semester_amount':ss.amount/(ss.end_semester-ss.start_semester+1)})
        funding_in_semester['scholarships'] = s        
        
        for semester_eligible_scholarship in semester_eligible_scholarships:
            if(semester_eligible_scholarship.start_semester != semester_eligible_scholarship.end_semester):
                semester_span = semester_eligible_scholarship.end_semester - semester_eligible_scholarship.start_semester + 1
                semester_total += semester_eligible_scholarship.amount/semester_span
            else:
                semester_total += semester_eligible_scholarship.amount
        for semester_other_funding in semester_other_fundings:
            if semester_other_funding.eligible:
                semester_total += semester_other_funding.amount
        funding_in_semester['semester_total'] = semester_total

        # grad status        
        status = None
        for s in GradStatus.objects.filter(student=grad):
            if s.start <= semester and (s.end == None or semester <= s.end) :
                status = s.get_status_display()
        
        # TAs
        ta_ra = []
        position_type = []
        amount = 0
        for contract in contracts:
            courses = []
            if contract.posting.semester == semester:
                position_type.append("TA")
                for course in TACourse.objects.filter(contract=contract):
                    amount += course.pay()
                    courses.append({'course': "%s (%s BU)" % (course.course.name(), course.bu),'amount': course.pay()})
                ta_ra.append({'type':"TA",'courses':courses,'amount':amount})

        # RAs   
        for appointment in appointments:
            courses = []
            app_start_sem = appointment.start_semester()
            app_end_sem = appointment.end_semester()
            length = appointment.semester_length()
            if app_start_sem <= semester and app_end_sem >= semester:
                position_type.append("RA")
                amount += appointment.lump_sum_pay/length
                courses.append({'course':"RA for %s - %s" % (appointment.hiring_faculty.name(), appointment.project), 'amount':appointment.lump_sum_pay/length })
            ta_ra.append({'type':"RA",'courses':courses,'amount':amount})
        
        funding_in_semester['semester_total'] += amount

        # promises (ending in this semester, so we display them in the right spot)
        try:
            promise = promises_qs.get(end_semester=semester)
        except Promise.DoesNotExist:
            promise = None
        
        semester_data = {'semester':semester, 'status':status,'funding_details':funding_in_semester,
                         'promise': promise,
                         'ta_ra': ta_ra, 'type': ', '.join(position_type)}
        #print semester_data
        semesters.append(semester_data)

    promises = []
    for promise in promises_qs:
        received = decimal.Decimal(0)
        for semester in semesters:
            if semester['semester'] < promise.start_semester or semester['semester'] > promise.end_semester:
                continue
            received += semester['funding_details']['semester_total']
        
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
