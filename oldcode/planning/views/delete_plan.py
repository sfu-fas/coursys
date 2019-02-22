from planning.models import SemesterPlan
from .admin_index import admin_index
from courselib.auth import requires_role
from log.models import LogEntry
from django.http import  HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404


@requires_role('PLAN')
def delete_plan(request, semester, plan_slug):
    plan = get_object_or_404(SemesterPlan, semester__name=semester, slug=plan_slug)
    if request.method == 'POST':
        plan.delete()

        #LOG EVENT#
        l = LogEntry(userid=request.user.username,
                  description=("deleted course plan %s in %s") % (plan.name, plan.semester),
                  related_object=request.user)
        l.save()

    messages.add_message(request, messages.SUCCESS, 'Plan deleted.')
    return HttpResponseRedirect(reverse(admin_index))
