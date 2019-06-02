from planning.models import SemesterPlan, PlannedOffering, MeetingTime
from coredata.models import Person, Role
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.template import RequestContext


@login_required
def view_plan(request, semester, plan_slug):
    userid = request.user.username
    person = get_object_or_404(Person, userid=userid)
    roles = Role.objects.filter(person=person)

    user = semester_visibility(roles)

    plan = get_object_or_404(SemesterPlan, slug=plan_slug, visibility__in=user)

    planned_offerings_list = PlannedOffering.objects.filter(plan=plan)
    meeting_time_list = [(MeetingTime.objects.filter(offering=p)) for p in planned_offerings_list]
    offerings_list = list(zip(planned_offerings_list, meeting_time_list))

    return render(request, "planning/view_plan.html", {'plan': plan, 'offerings_list': offerings_list, 'range': list(range(7))})


def semester_visibility(roles):
    user = ['ALL']

    for role in roles:
        if role.role == 'PLAN':
            user = ['ADMI', 'INST', 'ALL']
            break
        elif role.role == 'FAC' or role.role == 'SESS' or role.role == 'COOP':
            user = ['INST', 'ALL']

    return user
