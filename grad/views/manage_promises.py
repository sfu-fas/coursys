from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, Promise
from django.contrib import messages
from django.http import HttpResponseRedirect
from grad.forms import PromiseForm
from django.urls import reverse
from django.forms.utils import ErrorList
from coredata.models import Semester
from log.models import LogEntry

@requires_role("GRAD")
def manage_promises(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug = grad_slug)
    promises = Promise.objects.filter(student=grad).order_by('start_semester__name')
    
    if request.method == 'POST':
        form = PromiseForm(request.POST)
        if form.is_valid():
            try:
                promise = promises.get(end_semester=form.cleaned_data['end_semester'], removed=False)
            except Promise.DoesNotExist:
                promise = None

            if promise != None:
                form._errors['end_semester'] = ErrorList(["A Promise for this semester already exists."])
            else:
                promise = form.save(commit=False)
                promise.student = grad
                promise.save()
                messages.success(request, "Promise for %s sucessfully saved." % (grad))
                l = LogEntry(userid=request.user.username, 
                  description="added promise of $%f for %s" % (promise.amount, grad.slug),
                  related_object=promise )
                l.save()
                
                return HttpResponseRedirect(reverse('grad:manage_promises', kwargs={'grad_slug':grad.slug}))
    else:
        form = PromiseForm(initial={'student':grad, 'start_semester':Semester.get_semester(), 'end_semester':Semester.get_semester(), 'amount':'0.00'})
    
    context = {
                'grad':grad,
                'form': form,
                'promises': promises,
                'can_edit': True,
              }
    return render(request, 'grad/manage_promises.html', context)

