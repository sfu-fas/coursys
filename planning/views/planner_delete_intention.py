from planning.models import TeachingIntention
from planning.forms import *
from courselib.auth import requires_role
from coredata.models import Person, Semester
from django.shortcuts import get_object_or_404
from django.http import  HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse


@requires_role('PLAN')
def planner_delete_intention(request, semester, userid):
    instructor = get_object_or_404(Person, userid=userid)
    semester = get_object_or_404(Semester, name=semester)
    intention = get_object_or_404(TeachingIntention, semester=semester, instructor__userid=userid)

    messages.add_message(request, messages.SUCCESS, '%s plan for %s removed.' % (semester, instructor.name()))
    intention.delete()

    return HttpResponseRedirect(reverse('planning.views.view_intentions', kwargs={}))
