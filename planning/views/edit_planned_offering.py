from planning.models import *
from planning.forms import *
from update_plan import update_plan
from courselib.auth import requires_instructor
from courselib.auth import requires_role
from django.db.models import Q
from coredata.models import Person, Role, Semester, Member, CourseOffering, COMPONENT_CHOICES, CAMPUS_CHOICES, WEEKDAY_CHOICES 
from log.models import LogEntry
from django.contrib.auth.decorators import login_required
from django.forms.models import inlineformset_factory
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.template import Context, loader
from django.db.models import query
from django.db.utils import IntegrityError
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import datetime
from dashboard.models import *

@requires_role('PLAN')
def edit_planned_offering(request, semester, plan_slug, planned_offering_slug):
    offering = PlannedOffering.objects.get(slug=planned_offering_slug)
    meeting_time_list = MeetingTime.objects.filter(offering=offering)
    plan = SemesterPlan.objects.get(slug=plan_slug)

    courses = [(c.id, c.full_name()) for c in PlanningCourse.objects.filter(owner=plan.unit, status="OPEN").distinct()]

    MeetingTimeFormSet = inlineformset_factory(PlannedOffering, MeetingTime, extra=5)

    if request.method == 'POST':
        form = BaseOfferingBasicsForm(request.POST, instance=offering)
        form.fields['course'].choices = courses

        if form.is_valid():
            offering = form.save(commit=False)
            formset = MeetingTimeFormSet(request.POST, instance=offering, queryset=meeting_time_list)
            
            if formset.is_valid():
                offering.plan = plan

                try:
                    offering.save()
                except IntegrityError:
                    messages.add_message(request, messages.ERROR, 'This course already exists in the plan.')
                else:
                    form.save_m2m()
                    
                    formset.save()

                    #LOG EVENT#
                    l = LogEntry(userid=request.user.username,
                          description=("edited offering %s in %s") % (offering.course, offering.plan),
                          related_object=plan)
                    l.save()
                            
                    messages.add_message(request, messages.SUCCESS, 'Edited offering %s.' % (offering.course))

                    return HttpResponseRedirect(reverse('planning.views.update_plan', kwargs={'semester': semester, 'plan_slug': plan_slug}))
        else:
            formset = MeetingTimeFormSet(request.POST, queryset=meeting_time_list)
            messages.add_message(request, messages.ERROR, 'Error editing course.')
    else:
        form = BaseOfferingBasicsForm(instance=offering)
        form.fields['course'].choices = courses
        formset = MeetingTimeFormSet(instance=offering)
        
    return render_to_response("planning/edit_planned_offering.html",
        {'form': form, 'formset': formset, 'plan': plan, 'course': offering},
        context_instance=RequestContext(request))