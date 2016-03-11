from courselib.auth import requires_role
from coredata.models import Person, Unit
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.shortcuts import get_object_or_404
from log.models import LogEntry
from planning.models import PlanningCourse, TeachingCapability
from planning.forms import CapabilityForm


@requires_role('PLAN')
def planner_edit_capabilities(request, userid):
    instructor = get_object_or_404(Person, userid=userid)
    capability_list = TeachingCapability.objects.filter(instructor=instructor).order_by('course')
    unit_choices = Unit.objects.filter(role__role__in=["FAC", "SESS", "COOP"], role__person=instructor)

    possible_courses = [(c.id, c.full_name()) for c in PlanningCourse.objects.filter(owner__in=unit_choices, status="OPEN").distinct()]

    if request.method == 'POST':
        form = CapabilityForm(request.POST)
        form.fields['course'].choices = possible_courses

        form.instructor_id = instructor.id
        if form.is_valid():
            capability = form.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                      description=("Added %s as a teaching capability.") % (capability.course.full_name()),
                      related_object=capability)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Added teaching capability %s.' % (capability.course.full_name()))
            return HttpResponseRedirect(reverse('planning.views.planner_edit_capabilities', kwargs={'userid': userid}))
    else:
        form = CapabilityForm(initial={'instructor': instructor})
        form.fields['course'].choices = possible_courses

    return render_to_response("planning/planner_edit_capabilities.html",
                              {'instructor': instructor,
                               'capability_list': capability_list,
                               'form': form},
                              context_instance=RequestContext(request))
