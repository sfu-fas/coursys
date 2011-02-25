from planning.models import *
from courselib.auth import requires_advisor
from django.db.models import Q
from coredata.models import Person, Role, Semester, COMPONENT_CHOICES, CAMPUS_CHOICES, WEEKDAY_CHOICES 
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
def instructor_index(request):

	userid = request.user.username
	instructor = get_object_or_404(Person, userid = request.user.username)
	capability_list = TeachingCapability.objects.filter(instructor = instructor).order_by('course')
	intention_list = TeachingIntention.objects.filter(instructor = instructor).order_by('semester')
 		
	return render_to_response("planning/instructor_index.html",{'userid':userid, 'capability_list':capability_list, 'intention_list':intention_list},context_instance=RequestContext(request))

@login_required
def add_capability(request, userid):
   	
	course_list = Course.objects.filter()
	instructor = get_object_or_404(Person, userid = request.user.username)
	capability_list = TeachingCapability.objects.filter(instructor = instructor).order_by('course')
	
	return render_to_response("planning/add_capability.html",{'userid':userid, 'capability_list':capability_list, 'course_list':course_list},context_instance=RequestContext(request))

@login_required
def submit_capability(request, userid):
    
	course_number = request.POST['offering_courses']

	instructor = get_object_or_404(Person, userid = request.user.username)
	course = get_object_or_404(Course, number = course_number)
	
	added_capability = TeachingCapability(instructor = instructor, course = course)
	added_capability.save()
	
	messages.add_message(request, messages.SUCCESS, 'Submitted Successfully.')
	return HttpResponseRedirect(reverse(add_capability, kwargs={'userid':userid}))

@login_required
def add_intention(request, userid):

	semester_list = Semester.objects.filter()
	
	return render_to_response("planning/add_intention.html",{'userid':userid, 'semester_list':semester_list},context_instance=RequestContext(request))

@login_required
def submit_intention(request, userid):
	
	semester = request.POST['semester']
	course_count = request.POST['course_count']
	
	instructor = get_object_or_404(Person, userid = request.user.username)
	semester = get_object_or_404(Semester, name = semester)

	intention = TeachingIntention(instructor = instructor, semester = semester, count = course_count)
	intention.save()
	
	messages.add_message(request, messages.SUCCESS, 'Teaching Intention Submitted Successfully.')
	return HttpResponseRedirect(reverse(add_intention, kwargs={'userid':userid}))


	
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

	messages.add_message(request, messages.SUCCESS, 'Submit Successfully.')
	return HttpResponseRedirect(reverse(add_course, kwargs={'userid':userid}))

@login_required
def delete_course_from_capability(request, userid, course_id):

	course = TeachingCapability.objects.get(pk = course_id)
	course.delete()

	messages.add_message(request, messages.SUCCESS, 'Course Removed Successfully.')
	return HttpResponseRedirect(reverse(add_plan, kwargs={'userid':userid}))

#********************************************ADMIN************************************************************
@login_required
def admin_index(request):

	userid = request.user.username
	admin = get_object_or_404(Person, userid = request.user.username)
	plan_list = SemesterPlan.objects.filter().order_by('semester')

	return render_to_response("planning/admin_index.html",{'userid':userid, 'plan_list':plan_list},context_instance=RequestContext(request))

@login_required
def add_plan(request, userid):

	admin = get_object_or_404(Person, userid = request.user.username)
	semester_list = Semester.objects.filter()

	return render_to_response("planning/add_plan.html",{'userid':userid, 'semester_list':semester_list},context_instance=RequestContext(request))

@login_required
def submit_plan(request, userid):

	admin = get_object_or_404(Person, userid = request.user.username)

	input_semester = request.POST['semester']
	name = request.POST['plan_name']
	visibility = request.POST['visibility']
	active = False

	semester = get_object_or_404(Semester, name = input_semester)

	added_plan = SemesterPlan(semester = semester, name = name, visibility = visibility, active = active)
	added_plan.save()

	messages.add_message(request, messages.SUCCESS, 'Plan Submitted Successfully.')
	return HttpResponseRedirect(reverse(add_plan, kwargs={'userid':userid}))

@login_required
def edit_courses(request, userid, plan_id):

	semester_plan = get_object_or_404(SemesterPlan, pk = plan_id)

	#planned_courses_list = 
	#plan = PlannedOffering(plan = semester_plan, course = course, section = section, component = component, campus = campus)
	#plan.save()

	admin = get_object_or_404(Person, userid = request.user.username)
	course_list = Course.objects.filter()

	#return render_to_response("planning/edit_courses.html",{'userid':userid, 'course_list':course_list, 'planned_courses_list':planned_courses_list},context_instance=RequestContext(request))
	return render_to_response("planning/edit_courses.html",{'userid':userid, 'course_list':course_list},context_instance=RequestContext(request))

#********************************************ADMIN************************************************************






