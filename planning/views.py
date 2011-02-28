from planning.models import *
from courselib.auth import requires_advisor
from django.db.models import Q
from coredata.models import Person, Role, Semester, Member, COMPONENT_CHOICES, CAMPUS_CHOICES, WEEKDAY_CHOICES 
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

	instructor = get_object_or_404(Person, userid = request.user.username)
	semester_list = Semester.objects.filter()
	intention_list = TeachingIntention.objects.filter(instructor = instructor).order_by('semester')
	
	
	return render_to_response("planning/add_intention.html",{'userid':userid, 'semester_list':semester_list, 'intention_list':intention_list},context_instance=RequestContext(request))

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
	return HttpResponseRedirect(reverse(add_capability, kwargs={'userid':userid}))

#********************************************ADMIN************************************************************
@login_required
def admin_index(request):

	userid = request.user.username
	#admin = get_object_or_404(Person, userid = request.user.username)
	plan_list = SemesterPlan.objects.filter().order_by('semester')

	return render_to_response("planning/admin_index.html",{'userid':userid, 'plan_list':plan_list},context_instance=RequestContext(request))

@login_required
def add_plan(request, userid):

	#admin = get_object_or_404(Person, userid = request.user.username)
	semester_list = Semester.objects.filter()

	return render_to_response("planning/add_plan.html",{'userid':userid, 'semester_list':semester_list},context_instance=RequestContext(request))

def edit_plan(request, userid, plan_id):
	
	semester_list = Semester.objects.filter()
	semester_plan = get_object_or_404(SemesterPlan, pk = plan_id)
	
	
	return render_to_response("planning/edit_plan.html",{'userid':userid, 'plan_id':plan_id, 'semester_list':semester_list, 'semester_plan':semester_plan},context_instance=RequestContext(request))

@login_required
def submit_edited_plan(request, userid, plan_id):

	input_semester = request.POST['semester']
	name = request.POST['plan_name']
	visibility = request.POST['visibility']
	
	semester = get_object_or_404(Semester, name = input_semester)
	
	edited_plan = SemesterPlan.objects.get(pk = plan_id)

	edited_plan.name = name
	edited_plan.semester = semester
	edited_plan.visibility = visibility
	edited_plan.save()
	
	messages.add_message(request, messages.SUCCESS, 'Plan Edited Successfully.')
	return HttpResponseRedirect(reverse(admin_index))
	

@login_required
def submit_plan(request, userid):

	#admin = get_object_or_404(Person, userid = request.user.username)

	input_semester = request.POST['semester']
	name = request.POST['plan_name']
	visibility = request.POST['visibility']

	semester = get_object_or_404(Semester, name = input_semester)

	added_plan = SemesterPlan(semester = semester, name = name, visibility = visibility)
	added_plan.save()

	messages.add_message(request, messages.SUCCESS, 'Plan Submitted Successfully.')
	return HttpResponseRedirect(reverse(admin_index))

@login_required
def edit_courses(request, userid, plan_id):

	semester_plan = get_object_or_404(SemesterPlan, pk = plan_id)

	#admin = get_object_or_404(Person, userid = request.user.username)
	course_list = Course.objects.filter()
	planned_courses_list = PlannedOffering.objects.filter(plan = semester_plan)
	
	return render_to_response("planning/edit_courses.html",{'userid':userid, 'plan_id':plan_id, 'course_list':course_list, 'planned_courses_list':planned_courses_list},context_instance=RequestContext(request))

@login_required
def add_courses_to_plan(request, userid, plan_id):
	
	semester_plan = get_object_or_404(SemesterPlan, pk = plan_id)
	
	course_number = request.POST['offering_courses']
	course = get_object_or_404(Course, number = course_number)
	
	campus = request.POST['campus']
	component = request.POST['component']
	section = request.POST['section']
	
	added_course_to_plan = PlannedOffering(plan = semester_plan, course = course, campus = campus, component = component, section = section)
	added_course_to_plan.save()

	messages.add_message(request, messages.SUCCESS, 'Course Added Successfully.')
	return HttpResponseRedirect(reverse(edit_courses, kwargs={'userid':userid, 'plan_id':plan_id}))
	
@login_required
def delete_course_from_plan(request, userid, course_id, plan_id):
	
	course = PlannedOffering.objects.get(pk = course_id)
	course.delete()

	messages.add_message(request, messages.SUCCESS, 'Course Removed Successfully.')
	return HttpResponseRedirect(reverse(edit_courses, kwargs={'userid':userid, 'plan_id':plan_id}))
	

@login_required
def assign_instructors(request, userid, plan_id):

	semester_plan = get_object_or_404(SemesterPlan, pk = plan_id)

	course_list = Course.objects.filter()
	planned_courses_list = PlannedOffering.objects.filter(plan = semester_plan)
	
	instructor_list = TeachingCapability.objects.filter().order_by('instructor')
	instructor_intention_list = TeachingIntention.objects.filter(semester = semester_plan.semester, intentionfull = False)
		
	return render_to_response("planning/assign_instructors.html",{'userid':userid, 'plan_id':plan_id, 'course_list':course_list, 'planned_courses_list':planned_courses_list, 'instructor_list':instructor_list, 'instructor_intention_list':instructor_intention_list},context_instance=RequestContext(request))

@login_required
def submit_assigned_instructors(request, userid, course_id, plan_id):
	
	course = get_object_or_404(PlannedOffering, pk = course_id)
	semester_plan = get_object_or_404(SemesterPlan, pk = plan_id)
	
	instructor_id = request.POST['instructors']
	
	assigned_instructor = get_object_or_404(Person, userid = instructor_id)
	
	pre_instructor = course.instructor
	course.instructor = assigned_instructor
	course.save()
	
	intention_count = PlannedOffering.objects.filter(plan = semester_plan, instructor = assigned_instructor).count()	
	teaching_intention = TeachingIntention.objects.get(semester = semester_plan.semester, instructor = assigned_instructor)
	
	pre_intention_count = PlannedOffering.objects.filter(plan = semester_plan, instructor = pre_instructor).count()
	pre_teaching_intention = TeachingIntention.objects.get(semester = semester_plan.semester, instructor = pre_instructor)
	
	if intention_count >= teaching_intention.count:
		teaching_intention.intentionfull = True
		teaching_intention.save()
	else:
		teaching_intention.intentionfull = False
		teaching_intention.save()		

	if pre_intention_count >= pre_teaching_intention.count:
		pre_teaching_intention.intentionfull = True
		pre_teaching_intention.save()
	else:
		pre_teaching_intention.intentionfull = False
		pre_teaching_intention.save()
				
	messages.add_message(request, messages.SUCCESS, 'Instructor Assinged Successfully.')
	return HttpResponseRedirect(reverse(assign_instructors, kwargs={'userid':userid, 'plan_id':plan_id}))
	
@login_required
def activate_plan(request, plan_id):

	semester_plan = get_object_or_404(SemesterPlan, pk = plan_id)

	semester_plan.active = True
	semester_plan.save()

	messages.add_message(request, messages.SUCCESS, 'Plan Activated Successfully.')
	return HttpResponseRedirect(reverse(admin_index))
	
@login_required
def inactivate_plan(request, plan_id):

	semester_plan = get_object_or_404(SemesterPlan, pk = plan_id)

	semester_plan.active = False
	semester_plan.save()

	messages.add_message(request, messages.SUCCESS, 'Plan Inactivated Successfully.')
	return HttpResponseRedirect(reverse(admin_index))

@login_required
def delete_plan(request, plan_id):

	semester_plan = get_object_or_404(SemesterPlan, pk = plan_id)
	semester_plan.delete()

	#if PlannedOffering.objects.get(plan = semester_plan):
	#	plannedoffering = PlannedOffering.objects.get(plan = semester_plan)
	#	plannedoffering.delete()

	messages.add_message(request, messages.SUCCESS, 'Plan Deleted Successfully.')
	return HttpResponseRedirect(reverse(admin_index))
		
#********************************************ADMIN************************************************************






