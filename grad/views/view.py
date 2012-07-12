from courselib.auth import has_role, NotFoundResponse, ForbiddenResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, Supervisor, GradStatus, CompletedRequirement, GradRequirement, \
        Scholarship, OtherFunding, Promise, Letter

def _can_view_student(request, grad_slug):
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

@login_required
def view(request, grad_slug):
    grad, authtype = _can_view_student(request, grad_slug)
    if grad is None or authtype == 'student':
        return ForbiddenResponse(request)
    
    context = {'grad': grad}
    if 'section' in request.GET:
        # page sections fetched by AJAX calls
        section = request.GET['section']

        if section == 'general':
            return render(request, 'grad/view__general.html', context)

        elif section == 'committee':
            supervisors = Supervisor.objects.filter(student=grad).select_related('supervisor')
            context['supervisors'] = supervisors
            return render(request, 'grad/view__committee.html', context)

        elif section == 'status':
            status_history = GradStatus.objects.filter(student=grad, hidden=False).order_by('start__name')
            context['status_history'] = status_history
            return render(request, 'grad/view__status.html', context)

        elif section == 'requirements':
            completed_req = CompletedRequirement.objects.filter(student=grad).select_related('requirement').order_by('semester__name')
            req = GradRequirement.objects.filter(program=grad.program)
            missing_req = req    
            for s in completed_req:
                missing_req = missing_req.exclude(description=s.requirement.description)
            context['completed_req'] = completed_req
            context['missing_req'] = missing_req
            return render(request, 'grad/view__requirements.html', context)

        elif section == 'scholarships':
            scholarships = Scholarship.objects.filter(student=grad).select_related('scholarship_type').order_by('start_semester__name')
            context['scholarships'] = scholarships
            return render(request, 'grad/view__scholarships.html', context)

        elif section == 'otherfunding':
            otherfunding = OtherFunding.objects.filter(student=grad).order_by('semester__name')
            context['otherfunding'] = otherfunding
            return render(request, 'grad/view__otherfunding.html', context)

        elif section == 'promises':
            promises = Promise.objects.filter(student=grad).order_by('start_semester__name')
            context['promises'] = promises
            return render(request, 'grad/view__promises.html', context)

        elif section == 'letters':
            letters = Letter.objects.filter(student=grad).select_related('template').order_by('date')
            context['letters'] = letters
            return render(request, 'grad/view__letters.html', context)

        else:
            return NotFoundResponse(request)

    return render(request, 'grad/view.html', context)

