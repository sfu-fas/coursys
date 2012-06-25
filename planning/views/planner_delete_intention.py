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
def planner_delete_intention(request, semester, userid):
    instructor = get_object_or_404(Person, userid=userid)
    semester = get_object_or_404(Semester, name=semester)
    intention = get_object_or_404(TeachingIntention, semester=semester, instructor__userid=userid)

    messages.add_message(request, messages.SUCCESS, '%s plan for %s removed.' % (semester, instructor.name()))
    intention.delete()

    return HttpResponseRedirect(reverse('planning.views.view_intentions', kwargs={}))