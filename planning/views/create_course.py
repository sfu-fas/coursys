from planning.models import *
from planning.forms import *
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
def create_course(request):
    units = [(u.id, unicode(u)) for u in request.units]
    if request.method == 'POST':
        form = CourseForm(request.POST)
        form.fields['owner'].choices = units
        if form.is_valid():
            course = form.save()

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("added course %s %s") % (course.subject, course.number),
                  related_object=course)
            l.save()
                
            messages.add_message(request, messages.SUCCESS, 'Added course %s.' % (course))
            
            return HttpResponseRedirect(reverse('planning.views.manage_courses', kwargs={}))
    else:
        form = CourseForm()
        form.fields['owner'].choices = units

    return render_to_response("planning/create_course.html", {'form': form}, context_instance=RequestContext(request))