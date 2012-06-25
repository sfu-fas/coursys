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
def submit_intention(request, userid):
    semester = request.POST['semester']
    course_count = request.POST['course_count']
    
    instructor = get_object_or_404(Person, userid=request.user.username)
    semester = get_object_or_404(Semester, name=semester)

    intention = TeachingIntention(instructor=instructor, semester=semester, count=course_count)
    intention.save()
    
    messages.add_message(request, messages.SUCCESS, 'Teaching intention submitted successfully.')
    return HttpResponseRedirect(reverse(add_intention, kwargs={'userid':userid}))
