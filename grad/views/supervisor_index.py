from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from grad.models import Supervisor

@login_required
def supervisor_index(request):
    supervisors = Supervisor.objects.filter(supervisor__userid=request.user.username, removed=False) \
            .order_by('-student__start_semester') \
            .select_related('student__person', 'student__start_semester', 'student__program')
    context = {'supervisors': supervisors}
    return render(request, 'grad/supervisor_index.html', context)
