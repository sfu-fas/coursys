from courselib.auth import requires_role
from django.shortcuts import render, get_object_or_404, HttpResponse
from coredata.models import Semester
from grad.models import Promise
from datetime import datetime
import csv


@requires_role("GRAD", get_only=["GRPD"])
def all_promises(request, semester_name=None):
    if semester_name is None:
        semester = Semester.next_starting()
    else:
        semester = get_object_or_404(Semester, name=semester_name)
    promises = Promise.objects.filter(end_semester=semester, 
                                      student__program__unit__in=request.units, removed=False)
    context = {'promises': promises, 'semester': semester}
    return render(request, 'grad/all_promises.html', context)


@requires_role("GRAD", get_only=["GRPD"])
def download_promises(request, semester_name=None):
    if semester_name is None:
        semester = Semester.next_starting()
    else:
        semester = get_object_or_404(Semester, name=semester_name)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'inline; filename="promises-%s-%s.csv"' % (semester.name,
                                                                                 datetime.now().strftime('%Y%m%d'))
    writer = csv.writer(response)
    writer.writerow(['Student', 'Program', 'Start Semester', 'Status', 'Promised', 'Received', 'Difference'])
    promises = Promise.objects.filter(end_semester=semester,
                                      student__program__unit__in=request.units)
    for p in promises:
        student = p.student.person.sortname()
        program = p.student.program.label
        start = p.student.start_semester.label()
        status = p.student.get_current_status_display()
        promised = p.amount
        received = p.received()
        difference = p.difference()
        writer.writerow([student, program, start, status, promised, received, difference])

    return response