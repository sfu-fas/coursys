from planning.models import SemesterPlan, PlannedOffering, MeetingTime
from planning.forms import CopyPlanForm
from courselib.auth import requires_role
from log.models import LogEntry
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template import RequestContext


@requires_role('PLAN')
def copy_plan(request):
    if request.method == 'POST':
        form = CopyPlanForm(request.POST)
        if form.is_valid():

            copied_plan_name = form.cleaned_data['copy_plan_from']
            copied_plan = SemesterPlan.objects.get(name=copied_plan_name)
            copied_courses = PlannedOffering.objects.filter(plan=copied_plan).order_by('course')

            plan = form.save()

            for i in copied_courses:
                added_course = PlannedOffering(plan=plan, course=i.course, section=i.section, component=i.component, campus=i.campus, enrl_cap=i.enrl_cap)
                added_course.save()

                meeting_times = MeetingTime.objects.filter(offering=i)
                for m in meeting_times:
                    added_meeting_time = MeetingTime(offering=added_course, weekday=m.weekday, start_time=m.start_time, end_time=m.end_time, room=m.room)
                    added_meeting_time.save()

            l = LogEntry(userid=request.user.username,
                      description=("Copied course plan %s in %s") % (plan.name, plan.semester),
                      related_object=plan)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'New plan "%s" created.' % (plan.name))
            return HttpResponseRedirect(reverse('planning.views.admin_index', kwargs={}))
    else:
        form = CopyPlanForm()

    return render_to_response("planning/copy_plan.html", {'form': form}, context_instance=RequestContext(request))
