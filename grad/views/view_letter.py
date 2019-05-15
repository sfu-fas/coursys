from courselib.auth import requires_role, ForbiddenResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, Letter
from grad.views.view import _can_view_student


@login_required
def view_letter(request, grad_slug, letter_slug):
    grad, authtype, units = _can_view_student(request, grad_slug)
    if grad is None or authtype == 'student':
        return ForbiddenResponse(request)

    letter = get_object_or_404(Letter, slug=letter_slug)
    grad = get_object_or_404(GradStudent, person=letter.student.person, slug=grad.slug, program__unit__in=units)

    page_title = 'View Letter'  
    crumb = 'View' 
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'letter' : letter,
               'grad' : grad
               }
    return render(request, 'grad/view_letter.html', context)
