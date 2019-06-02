from planning.forms import PlanBasicsForm
from planning.models import PlanningCourse
from courselib.auth import requires_role
from log.models import LogEntry
from django.shortcuts import render_to_response
from django.http import  HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template import RequestContext


@requires_role('PLAN')
def create_plan(request):
    unit_choices = [(u.id, str(u)) for u in request.units]

    if request.method == 'POST':
        form = PlanBasicsForm(request.POST)
        if form.is_valid():
            plan = form.save()
            # update PlanningCourse objects for this unit
            PlanningCourse.create_for_unit(plan.unit)

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                      description=("Created course plan %s in %s") % (plan.name, plan.semester),
                      related_object=plan)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'New plan "%s" created.' % (plan.name))
            return HttpResponseRedirect(reverse('planning.views.admin_index', kwargs={}))
    else:
        form = PlanBasicsForm()
        form.fields['unit'].choices = unit_choices

    return render(request, "planning/create_plan.html", {'form': form})
