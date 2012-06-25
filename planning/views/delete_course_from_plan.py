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
def delete_course_from_plan(request, course_id, plan_id):
    course = PlannedOffering.objects.get(pk=course_id)
    course.delete()
    
    semester_plan = get_object_or_404(SemesterPlan, pk=plan_id)
    semester = semester_plan.semester.name

    messages.add_message(request, messages.SUCCESS, 'Course removed successfully.')
    return HttpResponseRedirect(reverse(update_plan, kwargs={'semester':semester, 'plan_slug':semester_plan.slug}))
