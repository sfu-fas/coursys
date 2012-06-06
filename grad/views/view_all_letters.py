from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent
from grad.models import Letter

@requires_role("GRAD")
def view_all_letters(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    letters = Letter.objects.filter(student=grad)

    page_title = 'Letters for ' + grad.person.last_name + "," + grad.person.first_name
    crumb = 'Letters'     
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'letters': letters,
               'grad' : grad                 
               }
    return render(request, 'grad/letters.html', context)
