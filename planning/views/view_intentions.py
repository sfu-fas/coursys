from planning.models import TeachingIntention
from courselib.auth import requires_role
from coredata.models import Semester
from django.shortcuts import render_to_response
from django.template import RequestContext


@requires_role('PLAN')
def view_intentions(request):
    semesters = Semester.objects.all().order_by('-end')
    intentions = []

    for s in semesters:
        intentions.append(TeachingIntention.objects.filter(semester=s))

    plans = zip(semesters, intentions)
    return render_to_response("planning/view_intentions.html", {'plans': plans}, context_instance=RequestContext(request))
