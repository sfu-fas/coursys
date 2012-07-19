from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, OtherFunding
from django.contrib import messages
from django.http import HttpResponseRedirect
from grad.forms import OtherFundingForm
from django.core.urlresolvers import reverse
from coredata.models import Semester

@requires_role("GRAD")
def manage_otherfunding(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug = grad_slug)
    otherfunding = OtherFunding.objects.filter(student=grad).order_by('semester__name')
    
    if request.method == 'POST':
        form = OtherFundingForm(request.POST)
        if form.is_valid():
            temp = form.save(commit=False)
            temp.student = grad
            temp.save()
            messages.success(request, "Other funding for %s sucessfully saved." % (grad))
            
            return HttpResponseRedirect(reverse('grad.views.manage_otherfunding', kwargs={'grad_slug':grad.slug}))
    else:
        form = OtherFundingForm(initial={'student':grad, 'semester':Semester.get_semester(), 'amount':'0.00'})
    
    context = {
                'grad':grad,
                'form': form,
                'otherfunding': otherfunding,
              }
    return render(request, 'grad/manage_otherfunding.html', context)
