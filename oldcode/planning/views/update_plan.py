from planning.models import SemesterPlan, PlanningCourse, PlannedOffering, MeetingTime
from planning.forms import OfferingBasicsForm
from courselib.auth import requires_role
from log.models import LogEntry
from django.forms.models import inlineformset_factory
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.contrib import messages
from django.template import RequestContext
from django.db.utils import IntegrityError


@requires_role('PLAN')
def update_plan(request, semester, plan_slug):
    plan = get_object_or_404(SemesterPlan, semester__name=semester, slug=plan_slug)

    courses = [(c.id, c.full_name()) for c in PlanningCourse.objects.filter(owner=plan.unit, status="OPEN").distinct()]
    MeetingTimeFormSet = inlineformset_factory(PlannedOffering, MeetingTime, can_delete=False, extra=18)

    if request.method == 'POST':
        form = OfferingBasicsForm(request.POST)
        form.fields['course'].choices = courses

        if form.is_valid():
            offering = form.save(commit=False)
            formset = MeetingTimeFormSet(request.POST, instance=offering)

            if formset.is_valid():
                offering.plan = plan
                num_of_lab = form.cleaned_data['lab_sections']

                try:
                    offering.save()
                except IntegrityError:
                    messages.add_message(request, messages.ERROR, 'This course already exists in the plan.')
                else:
                    form.save_m2m()

                    formset.save()

                    num_of_lab = int(num_of_lab)
                    if num_of_lab > 0:
                        for i in range(num_of_lab):
                            course = form.cleaned_data['course']
                            section = form.cleaned_data['section'][:2] + "%02i" % (i + 1)
                            component = "LAB"
                            campus = form.cleaned_data['campus']
                            enrl_cap = form.cleaned_data['enrl_cap']

                            added_lab_section = PlannedOffering(plan=plan, course=course, section=section, component=component, campus=campus, enrl_cap=enrl_cap)
                            added_lab_section.save()

                        #LOG EVENT#
                        l = LogEntry(userid=request.user.username,
                              description=("added offering %s in %s") % (offering.course, offering.plan),
                              related_object=plan)
                        l.save()

                    messages.add_message(request, messages.SUCCESS, 'Added course %s.' % (offering.course))

                    # Reset forms
                    form = OfferingBasicsForm()
                    form.fields['course'].choices = courses
                    formset = MeetingTimeFormSet()
        else:
            formset = MeetingTimeFormSet(request.POST)
            messages.add_message(request, messages.ERROR, 'Error adding course.')
    else:
        form = OfferingBasicsForm()
        form.fields['course'].choices = courses
        formset = MeetingTimeFormSet()

    planned_offerings_list = PlannedOffering.objects.filter(plan=plan)
    meeting_time_list = [(MeetingTime.objects.filter(offering=p)) for p in planned_offerings_list]
    offerings_list = list(zip(planned_offerings_list, meeting_time_list))

    return render(request, "planning/update_plan.html",
        {'form': form, 'formset': formset, 'plan': plan, 'offerings_list': offerings_list, 'range': list(range(7))},
        context_instance=RequestContext(request))
