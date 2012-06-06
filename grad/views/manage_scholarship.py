from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent
from django.contrib import messages
from django.http import HttpResponseRedirect
from grad.forms import ScholarshipForm
from django.core.urlresolvers import reverse
from coredata.models import Semester
from view_all import view_all

get_semester = Semester.get_semester

@requires_role("GRAD")
def manage_scholarship(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug = grad_slug)
    if request.method == 'POST':
        scholarship_form = ScholarshipForm(request.POST)
        if scholarship_form.is_valid():
            temp = scholarship_form.save(commit=False)
            temp.student = grad
            temp.save()
            messages.success(request, "Scholarship for %s sucessfully saved." % (grad))
            
            return HttpResponseRedirect(reverse(view_all, kwargs={'grad_slug':grad.slug}))
    else:
        scholarship_form = ScholarshipForm(initial={'student':grad, 'start_semester':get_semester(), 'end_semester':get_semester(), 'amount':'0.00'})

    page_title = "New Scholarship"
    crumb = "%s, %s" % (grad.person.last_name, grad.person.first_name)

    context = {'page_title':page_title,
                'crumb':crumb,
                'grad':grad,
                'scholarship_form': scholarship_form
    }
    return render(request, 'grad/manage_scholarship.html', context)
