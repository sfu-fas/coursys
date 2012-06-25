from planning.models import *
from planning.forms import *
from edit_capability import edit_capability
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
def delete_capability(request, course_id):
    instructor = get_object_or_404(Person, userid=request.user.username)
    teaching_capability = get_object_or_404(TeachingCapability, pk=course_id, instructor=instructor)
    course = get_object_or_404(Course, teachingcapability=teaching_capability)
    messages.add_message(request, messages.SUCCESS, '%s %s removed from teachable courses.' % (course.subject, course.number))
    teaching_capability.delete()

    return HttpResponseRedirect(reverse(edit_capability, kwargs={}))