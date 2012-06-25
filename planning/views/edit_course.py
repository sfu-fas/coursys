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
def edit_course(request, course_slug):
    course = get_object_or_404(Course, slug=course_slug)

    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("added course %s %s") % (course.subject, course.number),
                  related_object=course)
            l.save()
                
            messages.add_message(request, messages.SUCCESS, 'Added course %s.' % (course))
            
            return HttpResponseRedirect(reverse('planning.views.update_plan', kwargs={'semester': semester, 'plan_slug': plan_slug}))
    else:
        form = CourseForm()

    return render_to_response("planning/create_course.html", {'form': form, 'plan': plan, 'planned_offerings_list': planned_offerings_list}, context_instance=RequestContext(request))