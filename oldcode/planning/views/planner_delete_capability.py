from planning.models import TeachingCapability, Course
from .planner_edit_capabilities import planner_edit_capabilities
from courselib.auth import requires_role
from coredata.models import Person
from django.http import  HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404


@requires_role('PLAN')
def planner_delete_capability(request, userid, course_id):
    instructor = get_object_or_404(Person, userid=userid)
    teaching_capability = get_object_or_404(TeachingCapability, pk=course_id, instructor=instructor)
    course = get_object_or_404(Course, teachingcapability=teaching_capability)
    messages.add_message(request, messages.SUCCESS, '%s %s removed from teaching capabilities.' % (course.subject, course.number))
    teaching_capability.delete()

    return HttpResponseRedirect(reverse(planner_edit_capabilities, kwargs={'userid': userid}))
