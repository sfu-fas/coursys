from planning.models import TeachingIntention
from .planner_create_intention import planner_create_intention
from courselib.auth import requires_instructor
from coredata.models import Person, Semester
from django.shortcuts import get_object_or_404
from django.http import  HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse


@requires_instructor
def submit_intention(request, userid):
    semester = request.POST['semester']
    course_count = request.POST['course_count']

    instructor = get_object_or_404(Person, userid=request.user.username)
    semester = get_object_or_404(Semester, name=semester)

    intention = TeachingIntention(instructor=instructor, semester=semester, count=course_count)
    intention.save()

    messages.add_message(request, messages.SUCCESS, 'Teaching intention submitted successfully.')
    return HttpResponseRedirect(reverse(planner_create_intention, kwargs={'userid': userid}))
