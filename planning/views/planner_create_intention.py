from planning.forms import PlannerIntentionForm
from courselib.auth import requires_role
from coredata.models import Person
from log.models import LogEntry
from django.shortcuts import render_to_response
from django.http import  HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template import RequestContext


@requires_role('PLAN')
def planner_create_intention(request):
    instructors = Person.objects.filter(role__role__in=["FAC", "SESS", "COOP"], role__unit__in=request.units)
    instructor_list = [(i.id, i) for i in instructors]

    if request.method == 'POST':
        form = PlannerIntentionForm(request.POST)

        if form.is_valid():
            intention = form.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                      description=("added teaching intention for %s") % (intention.instructor),
                      related_object=intention)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Added semester plan for %s.' % (intention.instructor.name()))

            return HttpResponseRedirect(reverse('planning.views.view_intentions', kwargs={}))
    else:
        form = PlannerIntentionForm()
        form.fields['instructor'].choices = instructor_list

    return render_to_response("planning/planner_create_intention.html", {'form': form}, context_instance=RequestContext(request))
