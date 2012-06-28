from planning.models import *
from planning.forms import PlanBasicsForm
from courselib.auth import requires_role
from log.models import LogEntry
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template import RequestContext


@requires_role('PLAN')
def edit_plan(request, semester, plan_slug):
    plan = get_object_or_404(SemesterPlan, semester__name=semester, slug=plan_slug)

    if request.method == 'POST':
        form = PlanBasicsForm(request.POST, instance=plan)
        if form.is_valid():
            plan = form.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                      description=("Modified course plan %s in %s") % (plan.name, plan.semester),
                      related_object=plan)
            l.save()

            messages.add_message(request, messages.SUCCESS, 'Plan "%s" updated.' % (plan.name))
            return HttpResponseRedirect(reverse('planning.views.admin_index', kwargs={}))
    else:
        form = PlanBasicsForm(instance=plan)

    return render_to_response("planning/edit_plan.html", {'form': form, 'plan': plan}, context_instance=RequestContext(request))
