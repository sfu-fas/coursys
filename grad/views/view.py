from courselib.auth import has_role, NotFoundResponse, ForbiddenResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils.safestring import mark_safe
from grad.models import GradStudent, Supervisor, GradStatus, \
        CompletedRequirement, GradRequirement, Scholarship, GradScholarship, \
        OtherFunding, Promise, Letter, GradProgramHistory, \
        FinancialComment, ProgressReport, ExternalDocument
from tacontracts.models import TAContract
from ra.models import RARequest, RAAppointment
from ta.models import TAContract as OldTAContract
from visas.models import Visa

def _can_view_student(request, grad_slug, funding=False):
    """
    Return GradStudent object and authorization type if user is either
    (1) admin for the student's unit,
    (2) the student him-/herself,
    (3) a senior supervisor of the student,
    (4) is a grad director in the student's unit.
    
    Return None if no condition is met
    """
    # grad admins can view within their unit
    if has_role('GRAD', request):
        grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
        return grad, 'admin', request.units

    # funding admins can view some pages within their unit
    if funding and (has_role('FUND', request) or has_role('FDMA', request)):
        grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
        return grad, 'admin', request.units

    # grad directors can ONLY view within their unit
    if request.method=='GET' and has_role('GRPD', request):
        grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
        return grad, 'graddir', request.units

    # senior supervisors can see their students
    supervisors = Supervisor.objects.filter(supervisor__userid=request.user.username, student__slug=grad_slug, supervisor_type__in=['SEN','POT','COS','COM'], removed=False).select_related('student')
    supervisors = [sup for sup in supervisors if sup.can_view_details()]
    if request.method=='GET' and supervisors:
        grad = supervisors[0].student
        return grad, 'supervisor', [grad.program.unit]

    # students can see their own page
    students = GradStudent.objects.filter(slug=grad_slug, person__userid=request.user.username)
    if request.method=='GET' and students:
        return students[0], 'student', [students[0].program.unit]
        
    return None, None, None

all_sections = ['general', 'supervisors', 'status', 'requirements', 
                'scholarships', 'otherfunding', 'promises', 'progressreports',
                'tacontracts', 'ras',
                'financialcomments', 'letters', 'documents', 'visas']

@login_required
def view(request, grad_slug, section=None):
    grad, authtype, units = _can_view_student(request, grad_slug)
    if grad is None or authtype == 'student':
        return ForbiddenResponse(request)

    # uses of the cortez link routed through here to see if they're actually being used
    if 'cortez-bounce' in request.GET and 'cortezid' in grad.config:
        from log.models import LogEntry
        from django.shortcuts import redirect
        l = LogEntry(userid=request.user.username,
              description="used cortez link for %s" % (grad.slug,),
              related_object=grad )
        l.save()
        return redirect("https://cortez.cs.sfu.ca/grad/scripts/grabcurrent.asp?Identifier=" + grad.config['cortezid'])

    # Only an authtype ruled as "admin" by _can_view_student should be allowed to edit anything here.
    can_edit = authtype == 'admin'
    context = {
        'grad': grad, 
        'can_edit': can_edit,
        'authtype': authtype,
    }

    for s in all_sections:
        context[s+'_content'] = ''
    
    if 'section' in request.GET:
        # page sections fetched by AJAX calls
        section = request.GET['section']

    if section:
        if section not in all_sections:
            return NotFoundResponse(request)
        
        elif section == 'general':
            programhistory = GradProgramHistory.objects.filter(student=grad, program__unit__in=units).order_by('starting')
            context['programhistory'] = programhistory
            flag_values = grad.flags_and_values()
            context['extras'] = [ (title, grad.config[field]) for field, title in grad.tacked_on_fields if field in grad.config] 
            context['flag_values'] = flag_values
            return render(request, 'grad/view__general.html', context)

        elif section == 'supervisors':
            supervisors = Supervisor.objects.filter(student=grad, removed=False).select_related('supervisor')
            context['supervisors'] = supervisors
            return render(request, 'grad/view__supervisors.html', context)

        elif section == 'status':
            statuses = GradStatus.objects.filter(student=grad, hidden=False).order_by('start__name')
            context['statuses'] = statuses
            return render(request, 'grad/view__status.html', context)

        elif section == 'requirements':
            completed_req = CompletedRequirement.objects.filter(student=grad, removed=False)
            completed_gradreq_id = [cr.requirement_id for cr in completed_req if cr.removed==False]
            req = GradRequirement.objects.filter(program=grad.program, hidden=False)
            missing_req = req.exclude(id__in=completed_gradreq_id)
            context['completed_req'] = completed_req
            context['missing_req'] = missing_req
            return render(request, 'grad/view__requirements.html', context)

        elif section == 'scholarships':
            scholarships = Scholarship.objects.filter(student=grad, removed=False).select_related('scholarship_type').order_by('start_semester__name')
            comments = FinancialComment.objects.filter(student=grad, comment_type='SCO', removed=False).order_by('created_at')
            context['scholarships'] = scholarships
            context['scholarship_comments'] = comments
            sims_scholarships = GradScholarship.objects.filter(student=grad, removed=False).order_by('semester__name')
            context['sims_scholarships'] = sims_scholarships
            return render(request, 'grad/view__scholarships.html', context)

        elif section == 'otherfunding':
            otherfunding = OtherFunding.objects.filter(student=grad, removed=False).order_by('semester__name')
            context['otherfunding'] = otherfunding
            return render(request, 'grad/view__otherfunding.html', context)

        elif section == 'promises':
            promises = Promise.objects.filter(student=grad, removed=False).order_by('start_semester__name')
            context['promises'] = promises
            return render(request, 'grad/view__promises.html', context)

        elif section == 'tacontracts':
            tacontracts = TAContract.objects.filter(person=grad.person, status__in=['NEW', 'SGN'])
            oldcontracts = OldTAContract.objects.filter(application__person=grad.person)
            context['tacontracts'] = tacontracts
            context['oldcontracts'] = oldcontracts
            return render(request, 'grad/view__tacontracts.html', context)
        
        elif section == 'ras':
            ras = RARequest.objects.filter(person=grad.person, deleted=False, complete=True, draft=False)
            oldras = RAAppointment.objects.filter(person=grad.person, deleted=False)
            context['ras'] = ras
            context['oldras'] = oldras
            return render(request, 'grad/view__ras.html', context)

        elif section == 'financialcomments':
            comments = FinancialComment.objects.filter(student=grad, removed=False).order_by('created_at')
            context['financial_comments'] = comments
            return render(request, 'grad/view__financialcomments.html', context)
        
        elif section == 'letters':
            letters = Letter.objects.filter(student=grad, removed=False).select_related('template').order_by('date')
            context['letters'] = letters
            return render(request, 'grad/view__letters.html', context)
        
        elif section == 'progressreports':
            progressreports = ProgressReport.objects.filter(student=grad, 
                                                            removed=False)\
                                                            .order_by('date')
            context['progress_reports'] = progressreports
            return render(request, 'grad/view__progress.html', context)
        
        elif section == 'documents':
            documents = ExternalDocument.objects.filter(student=grad, 
                                                        removed=False)\
                                                        .order_by('date')
            context['documents'] = documents
            return render(request, 'grad/view__documents.html', context)

        elif section == 'visas':
            visas = Visa.get_visas([grad.person])
            context['visas'] = visas
            return render(request, 'grad/view__visas.html', context)

        else:
            raise ValueError("Not all sections handled by view code: " + repr(section))

    elif '_escaped_fragment_' in request.GET:
        # Implement google-suggested hash-bang workaround. Not terribly efficient, but probably uncommon.
        # https://developers.google.com/webmasters/ajax-crawling/docs/getting-started
        sections = request.GET['_escaped_fragment_'].split(',')
        for s in sections:
            resp = view(request, grad_slug, section=s)
            context[s+'_content'] = mark_safe(resp.content.decode('utf8'))

    other_grad = GradStudent.objects \
                 .filter(program__unit__in=units, person=grad.person) \
                 .exclude(id=grad.id)
    other_applicant = [x for x in other_grad if x.is_applicant()]
    other_grad = [x for x in other_grad if not x.is_applicant()]
    context['other_grad'] = other_grad
    context['other_applicant'] = other_applicant

    return render(request, 'grad/view.html', context)

