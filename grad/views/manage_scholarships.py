from courselib.auth import requires_role
from django.shortcuts import get_object_or_404, render
from grad.models import GradStudent, ScholarshipType, Scholarship, FinancialComment
from django.contrib import messages
from django.http import HttpResponseRedirect
from grad.forms import ScholarshipForm
from django.urls import reverse
from coredata.models import Semester
from log.models import LogEntry

get_semester = Semester.get_semester

@requires_role("GRAD")
def manage_scholarships(request, grad_slug):
    grad = get_object_or_404(GradStudent, slug = grad_slug)
    scholarship_type_choices = [(st.id, st.name) for st in ScholarshipType.objects.filter(unit__in=request.units, hidden=False).order_by('unit__slug', 'name')]
    scholarships = Scholarship.objects.filter(student=grad).select_related('scholarship_type').order_by('start_semester__name')
    comments = FinancialComment.objects.filter(student=grad, comment_type='SCO', removed=False).order_by('created_at')
    
    if request.method == 'POST':
        form = ScholarshipForm(request.POST)
        form.fields['scholarship_type'].choices = scholarship_type_choices
        if form.is_valid():
            schol = form.save(commit=False)
            schol.student = grad
            schol.save()
            messages.success(request, "Scholarship for %s sucessfully saved." % (grad))
            l = LogEntry(userid=request.user.username, 
              description="added scholarship of $%f for %s" % (schol.amount, grad.slug),
              related_object=schol )
            l.save()
            
            return HttpResponseRedirect(reverse('grad:manage_scholarships', kwargs={'grad_slug':grad.slug}))
    else:
        form = ScholarshipForm(initial={'student':grad, 'start_semester':get_semester(), 'end_semester':get_semester(), 'amount':'0.00'})
        form.fields['scholarship_type'].choices = scholarship_type_choices
        

    context = {
                'grad':grad,
                'form': form,
                'scholarships': scholarships,
                'scholarship_comments': comments,
                'can_edit': True,
    }
    return render(request, 'grad/manage_scholarships.html', context)
