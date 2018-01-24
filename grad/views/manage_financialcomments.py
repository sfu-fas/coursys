from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, FinancialComment
from django.contrib import messages
from django.http import HttpResponseRedirect
from grad.forms import FinancialCommentForm
from django.urls import reverse
from coredata.models import Semester
from log.models import LogEntry

@requires_role("GRAD", get_only=["GRPD"])
def manage_financialcomments(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug = grad_slug)
    financial_comments = FinancialComment.objects.filter(student=grad, removed=False).order_by('semester__name')
    
    if request.method == 'POST':
        form = FinancialCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.student = grad
            comment.created_by = request.user.username
            comment.save()
            messages.success(request, "Financial Comment for %s sucessfully saved." % (grad))
            l = LogEntry(userid=request.user.username, 
              description="added financial comment \"%s\" for %s" % (str(comment), grad.slug),
              related_object=comment )
            l.save()
            
            return HttpResponseRedirect(reverse('grad:manage_financialcomments', kwargs={'grad_slug':grad.slug}))
    else:
        form = FinancialCommentForm(initial={
                'student':grad, 
                'semester':Semester.get_semester(), 
                'created_by':request.user.username })
    
    context = {
                'grad':grad,
                'form': form,
                'financial_comments': financial_comments,
              }
    return render(request, 'grad/manage_financialcomments.html', context)
