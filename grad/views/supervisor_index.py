from django.contrib.auth.decorators import login_required
from django.shortcuts import render, HttpResponse
from grad.models import Supervisor
import csv
from datetime import datetime

@login_required
def supervisor_index(request):
    supervisors = Supervisor.objects.filter(supervisor__userid=request.user.username, removed=False) \
            .exclude(student__current_status='DELE') \
            .order_by('-student__start_semester') \
            .select_related('student__person', 'student__start_semester', 'student__program')
    context = {'supervisors': supervisors}
    return render(request, 'grad/supervisor_index.html', context)


@login_required
def download_my_grads_csv(request):
    supervisors = Supervisor.objects.filter(supervisor__userid=request.user.username, removed=False) \
            .exclude(student__current_status='DELE') \
            .order_by('-student__start_semester') \
            .select_related('student__person', 'student__start_semester', 'student__program')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'inline; filename="%s.csv"' % datetime.now().strftime('%Y%m%d')
    writer = csv.writer(response)
    writer.writerow(['Name', 'Program', 'YourRole', 'StartSemester', 'EndSemester', 'ThesisTitle', 'CurrentStatus'])
    for s in supervisors:
        name = s.student.person.sortname()
        program = s.student.program.description
        role = s.get_supervisor_type_display()
        if s.supervisor_type == 'POT':
            if s.student.has_committee():
                role += ' (has committee)'
            else:
                role += ' (no committee)'
        start = s.student.start_semester
        end = s.student.end_semester
        status = s.student.get_current_status_display()
        title = s.student.config.get('work_title')
        writer.writerow([name, program, role, start, end, title, status])

    return response
