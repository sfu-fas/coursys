from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from grad.models import GradStudent
from django.http import HttpResponseRedirect
from django.urls import reverse

@login_required
def student_financials(request):
    grad = get_object_or_404(GradStudent, person__userid=request.user.username)
    # TODO: Even though there should only be one grad, 
    # figure out the right grad student entry to use
    # in case there are multiple
    return HttpResponseRedirect(reverse('grad:financials',kwargs={'grad_slug': grad.slug})) 
