from planning.models import PlanningCourse
from courselib.auth import requires_role
from django.shortcuts import render_to_response
from django.template import RequestContext


@requires_role('PLAN')
def manage_courses(request):
    course_list = PlanningCourse.objects.filter(owner__in=request.units, status="OPEN")
    return render_to_response("planning/manage_courses.html", {'course_list': course_list}, context_instance=RequestContext(request))
