from planning.models import TeachingCapability, Course
from .edit_capability import edit_capability
from courselib.auth import requires_instructor
from coredata.models import Person
from django.http import  HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404


@requires_instructor
def delete_capability(request, course_id):
    instructor = get_object_or_404(Person, userid=request.user.username)
    teaching_capability = get_object_or_404(TeachingCapability, pk=course_id, instructor=instructor)
    course = get_object_or_404(Course, teachingcapability=teaching_capability)
    messages.add_message(request, messages.SUCCESS, '%s %s removed from teaching capabilities.' % (course.subject, course.number))
    teaching_capability.delete()

    return HttpResponseRedirect(reverse(edit_capability, kwargs={}))
