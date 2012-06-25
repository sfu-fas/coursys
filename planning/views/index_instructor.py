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

@requires_instructor
def instructor_index(request):
    instructor = get_object_or_404(Person, userid=request.user.username)
    capability_list = TeachingCapability.objects.filter(instructor=instructor).order_by('course')
    intention_list = TeachingIntention.objects.filter(instructor=instructor).order_by('semester')

    return render_to_response("planning/instructor_index.html", {'capability_list':capability_list, 'intention_list':intention_list}, context_instance=RequestContext(request))
