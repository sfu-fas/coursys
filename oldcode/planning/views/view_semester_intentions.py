from planning.models import TeachingIntention
from courselib.auth import requires_role
from coredata.models import Semester
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.shortcuts import get_object_or_404


@requires_role('PLAN')
def view_semester_intentions(request, semester):
    semester = get_object_or_404(Semester, name=semester)
    intentions = TeachingIntention.objects.filter(semester=semester)

    return render_to_response("planning/view_semester_intentions.html", {'semester': semester, 'intentions': intentions}, context_instance=RequestContext(request))
