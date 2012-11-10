from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent
from grad.models import Letter

@requires_role("GRAD", get_only=["GRPD"])
def manage_letters(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    letters = Letter.objects.filter(student=grad)

    context = {
               'letters': letters,
               'grad' : grad                 
               }
    return render(request, 'grad/manage_letters.html', context)
