from planning.models import *
from planning.forms import *
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

@login_required
def view_plan(request, semester, plan_slug):
    userid = request.user.username
    person = get_object_or_404(Person, userid=userid)
    roles = Role.objects.filter(person=person)

    user = semester_visibility(roles)

    plan = get_object_or_404(SemesterPlan, slug=plan_slug, visibility__in=user)

    planned_offerings_list = PlannedOffering.objects.filter(plan=plan)
    
    return render_to_response("planning/view_plan.html", {'plan':plan, 'planned_offerings_list': planned_offerings_list}, context_instance=RequestContext(request))


def semester_visibility(roles):
    user = ['ALL']

    for role in roles:
        if role.role == 'PLAN':
            user = ['ADMI', 'INST', 'ALL']
            break
        elif role.role == 'FAC' or role.role == 'SESS' or role.role == 'COOP':
            user = ['INST', 'ALL']

    return user