from courselib.auth import requires_role
from django.shortcuts import render, get_object_or_404
from coredata.models import Semester
from grad.models import Promise

@requires_role("GRAD", get_only=["GRPD"])
def all_promises(request, semester_name=None):
    if semester_name is None:
        semester = Semester.next_starting()
    else:
        semester = get_object_or_404(Semester, name=semester_name)
    promises = Promise.objects.filter(end_semester=semester)
    context = {'promises': promises, 'semester': semester}
    return render(request, 'grad/all_promises.html', context)
