from planning.models import TeachingIntention
from courselib.auth import requires_role
from coredata.models import Semester
from django.shortcuts import render_to_response
from django.template import RequestContext


@requires_role('PLAN')
def view_intentions(request):
    semester = Semester.get_semester()
    semester_list = [semester]
    if (semester.next_semester()):
        semester = semester.next_semester()
        semester_list.append(semester)
    if (semester.next_semester()):
        semester = semester.next_semester()
        semester_list.append(semester)

    intentions = []

    for s in semester_list:
        intentions.append(TeachingIntention.objects.filter(semester=s))

    semesters = Semester.objects.all()

    plans = zip(semester_list, intentions)
    return render_to_response("planning/view_intentions.html", {'plans': plans, 'semesters': semesters}, context_instance=RequestContext(request))
