from planning.models import SemesterPlan
from coredata.models import Person, Role
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.template import RequestContext


@login_required
def plans_index(request):
    userid = request.user.username
    person = get_object_or_404(Person, userid=userid)
    roles = Role.objects.filter(person=person)

    user = semester_visibility(roles)

    plan_list = SemesterPlan.objects.filter(visibility__in=user).order_by('semester')

    return render_to_response("planning/plans_index.html", {'userid': userid, 'plan_list': plan_list}, context_instance=RequestContext(request))


def semester_visibility(roles):
    user = ['ALL']

    for role in roles:
        if role.role == 'PLAN':
            user = ['ADMI', 'INST', 'ALL']
            break
        elif role.role == 'FAC' or role.role == 'SESS' or role.role == 'COOP':
            user = ['INST', 'ALL']

    return user
