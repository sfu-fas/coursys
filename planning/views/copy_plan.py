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

            l = LogEntry(userid=request.user.username,
                      description=("Copied course plan %s in %s") % (plan.name, plan.semester),
                      related_object=plan)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'New plan "%s" created.' % (plan.name))
            return HttpResponseRedirect(reverse('planning.views.admin_index', kwargs={}))
    else:
        form = CopyPlanForm()

    return render_to_response("planning/copy_plan.html",{'form':form},context_instance=RequestContext(request))
