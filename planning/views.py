from planning.models import *
from courselib.auth import requires_advisor
from django.db.models import Q
from coredata.models import Person, Member, Role
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.template import Context, loader
from django.db.models import query
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import datetime

@login_required
def courses(request):

	userid = request.user.username
	return render_to_response("planning/index.html",{'userid':userid},context_instance=RequestContext(request))
	

@login_required
def add_plan(request, userid):
    
	return HttpResponse(userid)
	

@login_required
def add_course(request, userid):

	return render_to_response("planning/add_courses.html",{'userid':userid},context_instance=RequestContext(request))

@login_required
def submit_course(request, userid):

	subject = request.POST['course_subject']
	number = request.POST['course_number']
	title = request.POST['course_title']
	
	added_course = Course(subject = subject, number = number, title = title)
	added_course.save();

	messages.add_message(request, messages.SUCCESS, 'Submit successfully.')
	return HttpResponseRedirect(reverse(add_course, kwargs={'userid':userid}))

#	return	HttpResponse("submit success")













