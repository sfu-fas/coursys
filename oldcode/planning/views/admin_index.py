from planning.models import SemesterPlan
from courselib.auth import requires_role
from django.shortcuts import render_to_response
from django.template import RequestContext


@requires_role('PLAN')
def admin_index(request):
    plan_list = SemesterPlan.objects.filter(unit__in=request.units).order_by('semester')

    return render(request, "planning/admin_index.html", {'plan_list': plan_list})
