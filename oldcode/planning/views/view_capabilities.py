from planning.models import TeachingCapability, PlanningCourse
from courselib.auth import requires_role
from coredata.models import Person
from django.shortcuts import render_to_response
from django.template import RequestContext


@requires_role('PLAN')
def view_capabilities(request):
    instructors = Person.objects.filter(role__role__in=["FAC", "SESS", "COOP"],
                                        role__unit__in=request.units)
    capabilities = []
    for i in instructors:
        capabilities.append(TeachingCapability.objects.filter(instructor=i))
    capabilities_list = list(zip(instructors, capabilities))

    courses = PlanningCourse.objects.filter(owner__in=request.units)
    capabilities = []
    for c in courses:
        capabilities.append(TeachingCapability.objects.filter(course=c))
    course_capabilities_list = list(zip(courses, capabilities))

    return render(request, "planning/view_capabilities.html",
                              {'capabilities_list': capabilities_list,
                               'course_capabilities_list': course_capabilities_list},
                              context_instance=RequestContext(request))
