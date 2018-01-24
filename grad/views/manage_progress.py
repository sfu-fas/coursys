from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, ProgressReport
from django.contrib import messages
from django.http import HttpResponseRedirect
from grad.forms import ProgressReportForm
from django.urls import reverse
from log.models import LogEntry

@requires_role("GRAD")
def manage_progress(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug = grad_slug)
    progress_reports = ProgressReport.objects.filter(student=grad).order_by('date')
    
    if request.method == 'POST':
        form = ProgressReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.student = grad
            report.save()
            messages.success(request, "Progress Report for %s sucessfully saved." % (grad))
            l = LogEntry(userid=request.user.username, 
              description="added progress report for %s" % (grad.slug,),
              related_object=report )
            l.save()
            
            return HttpResponseRedirect(reverse('grad:manage_progress', kwargs={'grad_slug':grad.slug}))
    else:
        form = ProgressReportForm()
    
    context = {
                'grad':grad,
                'form': form,
                'progress_reports': progress_reports,
                'can_edit': True,
              }
    return render(request, 'grad/manage_progress.html', context)

