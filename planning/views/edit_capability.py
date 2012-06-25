from planning.models import *
from planning.forms import *
from courselib.auth import requires_instructor
from coredata.models import Person
from log.models import LogEntry
from django.forms.models import inlineformset_factory
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template import RequestContext

@requires_instructor
def edit_capability(request):
    instructor = get_object_or_404(Person, userid=request.user.username)
    capability_list = TeachingCapability.objects.filter(instructor=instructor).order_by('course')
    unit_choices = request.units

    possible_courses = [(c.id, c.full_name()) for c in PlanningCourse.objects.filter(owner__in=unit_choices, status="OPEN").distinct()]

    if request.method == 'POST':
        form = CapabilityForm(request.POST)
        form.fields['course'].choices = possible_courses

        form.instructor_id = instructor.id
        if form.is_valid():
            capability = form.save()
            
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                      description=("Added teaching capability %s") % (capability.course.full_name()),
                      related_object=capability)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Added teaching capability %s.' % (capability.course.full_name()))
            return HttpResponseRedirect(reverse('planning.views.edit_capability', kwargs={}))
    else:
        form = CapabilityForm(initial={'instructor':instructor})
        form.fields['course'].choices = possible_courses
    
    return render_to_response("planning/edit_capability.html", {'capability_list': capability_list, 'form': form}, context_instance=RequestContext(request))