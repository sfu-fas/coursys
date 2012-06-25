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
def create_plan(request):
    unit_choices = [(u.id, unicode(u)) for u in request.units]

    if request.method == 'POST':
        form = PlanBasicsForm(request.POST)
        if form.is_valid():
            plan = form.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                      description=("Created course plan %s in %s") % (plan.name, plan.semester),
                      related_object=plan)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'New plan "%s" created.' % (plan.name))
            return HttpResponseRedirect(reverse('planning.views.admin_index', kwargs={}))
    else:
        form = PlanBasicsForm()
        form.fields['unit'].choices = unit_choices
    
    return render_to_response("planning/create_plan.html",{'form':form},context_instance=RequestContext(request))