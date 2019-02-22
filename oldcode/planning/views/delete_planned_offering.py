from planning.models import PlannedOffering
from .update_plan import update_plan
from courselib.auth import requires_role
from django.http import  HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse


@requires_role('PLAN')
def delete_planned_offering(request, semester, plan_slug, planned_offering_slug):
    course = PlannedOffering.objects.get(slug=planned_offering_slug)
    course.delete()

    messages.add_message(request, messages.SUCCESS, 'Course removed successfully.')
    return HttpResponseRedirect(reverse(update_plan, kwargs={'semester': semester, 'plan_slug': plan_slug}))
