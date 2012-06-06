from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, Letter

@requires_role("GRAD")
def view_letter(request, letter_slug):
    letter = get_object_or_404(Letter, slug=letter_slug)
    grad = get_object_or_404(GradStudent, person=letter.student.person)

    page_title = 'View Letter'  
    crumb = 'View' 
    context = {
               'page_title' : page_title,
               'crumb' : crumb,
               'letter' : letter,
               'grad' : grad
               }
    return render(request, 'grad/view_letter.html', context)
