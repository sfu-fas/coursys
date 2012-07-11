from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent
from django.contrib import messages
from django.http import HttpResponseRedirect
from grad.forms import PromiseForm
import datetime
from django.core.urlresolvers import reverse
from coredata.models import Semester

get_semester = Semester.get_semester

@requires_role("GRAD")
def new_promise(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug=grad_slug)
    if request.method == 'POST':
        promise_form = PromiseForm(request.POST)
        if promise_form.is_valid():
            temp = promise_form.save(commit=False)
            temp.student = grad
            temp.save()
            messages.success(request, "Promise amount %s saved for %s." % (promise_form.cleaned_data['amount'], grad))
            
            return HttpResponseRedirect(reverse('grad.views.view', kwargs={'grad_slug':grad.slug}))
    else:
        promise_form = PromiseForm(initial={'start_semester': get_semester().offset(1), 'end_semester': get_semester().offset(3), 'amount':'0.00'})

    page_title = "New Promise"
    crumb = "%s, %s" % (grad.person.last_name, grad.person.first_name)

    context = {'page_title':page_title,
                'crum':crumb,
                'grad':grad,
                'Promise_form': promise_form
    }
    return render(request, 'grad/manage_promise.html', context)
