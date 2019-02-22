from planning.models import TeachingIntention
from .edit_intention import edit_intention
from courselib.auth import requires_instructor
from coredata.models import Person, Semester
from django.http import  HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404


@requires_instructor
def delete_intention(request, semester):
    instructor = get_object_or_404(Person, userid=request.user.username)
    teaching_intention = get_object_or_404(TeachingIntention, semester__name=semester, instructor=instructor)
    semester = get_object_or_404(Semester, name=semester)
    messages.add_message(request, messages.SUCCESS, '%s plan removed.' % (semester))
    teaching_intention.delete()

    return HttpResponseRedirect(reverse(edit_intention, kwargs={}))
