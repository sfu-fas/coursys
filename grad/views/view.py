from courselib.auth import has_role, NotFoundResponse, ForbiddenResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils.safestring import mark_safe
from grad.models import GradStudent, Supervisor, GradStatus, CompletedRequirement, GradRequirement, \
        Scholarship, OtherFunding, Promise, Letter, GradProgramHistory, FinancialComment

def _can_view_student(request, grad_slug, funding=False):
    """
    Return GradStudent object and authorization type if user is either
    (1) admin for the student's unit,
    (2) the student him-/herself,
    (3) a senior supervisor of the student.
    
    Return None if neither condition is met
    """
    # grad admins can view within their unit
    if has_role('GRAD', request):
        grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
        return grad, 'admin'

    # funding admins can view some pages within their unit
    if funding and has_role('FUND', request):
        grad = get_object_or_404(GradStudent, slug=grad_slug, program__unit__in=request.units)
        return grad, 'admin'

    # students can see their own page
    students = GradStudent.objects.filter(slug=grad_slug, person__userid=request.user.username)
    if students:
        return students[0], 'student'
        
    # senior supervisors can see their students
    supervisors = Supervisor.objects.filter(supervisor__userid=request.user.username, student__slug=grad_slug, supervisor_type='SEN').select_related('student')
    if supervisors:
        grad = supervisors[0].student
        return grad, 'supervisor'

    return None, None

all_sections = ['general', 'supervisors', 'status', 'requirements', 
                'scholarships', 'otherfunding', 'promises', 'financialcomments', 'letters']

@login_required
def view(request, grad_slug, section=None):
    grad, authtype = _can_view_student(request, grad_slug)
    if grad is None or authtype == 'student':
        return ForbiddenResponse(request)
    
    context = {
        'grad': grad, 
        'index': True, 
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
            programhistory = GradProgramHistory.objects.filter(student=grad, program__unit__in=request.units)
            context['programhistory'] = programhistory
            flag_values = grad.flags_and_values()
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
            return render(request, 'grad/view__scholarships.html', context)

        elif section == 'otherfunding':
            otherfunding = OtherFunding.objects.filter(student=grad, removed=False).order_by('semester__name')
            context['otherfunding'] = otherfunding
            return render(request, 'grad/view__otherfunding.html', context)

        elif section == 'promises':
            promises = Promise.objects.filter(student=grad, removed=False).order_by('start_semester__name')
            context['promises'] = promises
            return render(request, 'grad/view__promises.html', context)
        
        elif section == 'financialcomments':
            comments = FinancialComment.objects.filter(student=grad, removed=False).order_by('created_at')
            context['financial_comments'] = comments
            return render(request, 'grad/view__financialcomments.html', context)
        
        elif section == 'letters':
            letters = Letter.objects.filter(student=grad).select_related('template').order_by('date')
            context['letters'] = letters
            return render(request, 'grad/view__letters.html', context)

        else:
            raise ValueError, "Not all sections handled by view code: " + repr(section)

    elif '_escaped_fragment_' in request.GET:
        # Implement google-suggested hash-bang workaround. Not terribly efficient, but probably uncommon.
        # https://developers.google.com/webmasters/ajax-crawling/docs/getting-started
        sections = request.GET['_escaped_fragment_'].split(',')
        for s in sections:
            resp = view(request, grad_slug, section=s)
            context[s+'_content'] = mark_safe(resp.content)

    other_grad = GradStudent.objects \
                 .filter(program__unit__in=request.units, person=grad.person) \
                 .exclude(id=grad.id)
    context['other_grad'] = other_grad

    return render(request, 'grad/view.html', context)

