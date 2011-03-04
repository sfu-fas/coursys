from planning.models import *
from planning.forms import *
from courselib.auth import requires_instructor, requires_role
from django.db.models import Q
from coredata.models import Person, Role, Semester, Member, COMPONENT_CHOICES, CAMPUS_CHOICES, WEEKDAY_CHOICES 
from log.models import LogEntry
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

@requires_instructor
def instructor_index(request):
	instructor = get_object_or_404(Person, userid = request.user.username)
	capability_list = TeachingCapability.objects.filter(instructor = instructor).order_by('course')
	intention_list = TeachingIntention.objects.filter(instructor = instructor).order_by('semester')
 		
	return render_to_response("planning/instructor_index.html",{'capability_list':capability_list, 'intention_list':intention_list},context_instance=RequestContext(request))

@requires_instructor
def edit_capability(request):
	instructor = get_object_or_404(Person, userid = request.user.username)
	capability_list = TeachingCapability.objects.filter(instructor = instructor).order_by('course')
	if request.method == 'POST':
	    form = CapabilityForm(request.POST)
	    form.instructor_id = instructor.id
	    if form.is_valid():
	        capability = form.save()
	        
	        #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("added teaching capability %s") % (capability.course.short_str()),
                      related_object=capability)
                l.save()
                messages.add_message(request, messages.SUCCESS, 'Added teaching capability %s.' % (capability.course.short_str()))
	        return HttpResponseRedirect(reverse('planning.views.edit_capability', kwargs={}))
	else:
	    form = CapabilityForm(initial={'instructor':instructor})
	
	return render_to_response("planning/add_capability.html",{'capability_list': capability_list, 'form':form},context_instance=RequestContext(request))

@requires_instructor
def edit_intention(request):
	instructor = get_object_or_404(Person, userid=request.user.username)
	semester_list = Semester.objects.filter()
	intention_list = TeachingIntention.objects.filter(instructor = instructor).order_by('semester')
	
	if request.method == 'POST':
	    form = IntentionForm(request.POST)
	    form.instructor_id = instructor.id
	    if form.is_valid():
	        intention = form.save()
	        
	        #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("added teaching intention for %s") % (intention.semester),
                      related_object=intention)
                l.save()
                messages.add_message(request, messages.SUCCESS, 'Added semester plan for %s.' % (intention.semester))
	        return HttpResponseRedirect(reverse('planning.views.edit_intention', kwargs={}))
	else:
	    form = IntentionForm(initial={'instructor':instructor})
	
	return render_to_response("planning/add_intention.html",{'form':form, 'intention_list':intention_list},context_instance=RequestContext(request))

@requires_instructor
def submit_intention(request, userid):
	
	semester = request.POST['semester']
	course_count = request.POST['course_count']
	
	instructor = get_object_or_404(Person, userid = request.user.username)
	semester = get_object_or_404(Semester, name = semester)

	intention = TeachingIntention(instructor = instructor, semester = semester, count = course_count)
	intention.save()
	
	messages.add_message(request, messages.SUCCESS, 'Teaching Intention Submitted Successfully.')
	return HttpResponseRedirect(reverse(add_intention, kwargs={'userid':userid}))


	
@requires_role('PLAN')
def add_course(request):

	return render_to_response("planning/add_courses.html",{},context_instance=RequestContext(request))

@requires_role('PLAN')
def submit_course(request):

	subject = request.POST['course_subject']
	number = request.POST['course_number']
	title = request.POST['course_title']
	
	added_course = Course(subject = subject, number = number, title = title)
	added_course.save();

	messages.add_message(request, messages.SUCCESS, 'Course %s %s added.' % (subject, number))
	return HttpResponseRedirect(reverse('planning.views.admin_index', kwargs={}))

@requires_instructor
def delete_course_from_capability(request, course_id):
	instructor = get_object_or_404(Person, userid=request.user.username)
	course = get_object_or_404(TeachingCapability, pk=course_id, instructor=instructor)
	messages.add_message(request, messages.SUCCESS, '%s %s removed from teachable courses.' % (course.course.subject, course.course.number))
	course.delete()

	return HttpResponseRedirect(reverse(edit_capability, kwargs={}))

#********************************************ADMIN************************************************************
@requires_role('PLAN')
def admin_index(request):

	userid = request.user.username
	#admin = get_object_or_404(Person, userid = request.user.username)
	plan_list = SemesterPlan.objects.filter().order_by('semester')

	return render_to_response("planning/admin_index.html",{'userid':userid, 'plan_list':plan_list},context_instance=RequestContext(request))

@requires_role('PLAN')
def add_plan(request):
	if request.method == 'POST':
	    form = PlanBasicsForm(request.POST)
	    if form.is_valid():
	        plan = form.save()
	        
	        #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("created course plan %s in %s") % (plan.name, plan.semester),
                      related_object=plan)
                l.save()
                messages.add_message(request, messages.SUCCESS, 'New plan "%s" created.' % (plan.name))
	        return HttpResponseRedirect(reverse('planning.views.admin_index', kwargs={}))
	else:
	    form = PlanBasicsForm()
	
	return render_to_response("planning/add_plan.html",{'form':form},context_instance=RequestContext(request))

@requires_role('PLAN')
def edit_plan(request, semester, plan_slug):
	plan = get_object_or_404(SemesterPlan, semester__name=semester, slug=plan_slug)
	if request.method == 'POST':
	    form = PlanBasicsForm(request.POST, instance=plan)
	    if form.is_valid():
	        plan = form.save()
	        
	        #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("created course plan %s in %s") % (plan.name, plan.semester),
                      related_object=plan)
                l.save()
                
                messages.add_message(request, messages.SUCCESS, 'Plan "%s" updated.' % (plan.name))
	        return HttpResponseRedirect(reverse('planning.views.admin_index', kwargs={}))
	else:
	    form = PlanBasicsForm(instance=plan)
	
	return render_to_response("planning/edit_plan.html",{'form':form, 'plan':plan},context_instance=RequestContext(request))

@requires_role('PLAN')
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
	

@requires_role('PLAN')
def edit_courses(request, semester, plan_slug):
	plan = get_object_or_404(SemesterPlan, semester__name=semester, slug=plan_slug)
	planned_courses_list = PlannedOffering.objects.filter(plan=plan)
	if request.method == 'POST':
	    form = OfferingBasicsForm(request.POST)
	    if form.is_valid():
	        offering = form.save(commit=False)
	        offering.plan = plan
	        offering.save()
	        form.save_m2m()
	        
	        #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("added offering %s in %s") % (offering.course, offering.plan),
                      related_object=plan)
                l.save()
                
                messages.add_message(request, messages.SUCCESS, 'Added course %s.' % (offering.course))
	        #return HttpResponseRedirect(reverse('planning.views.admin_index', kwargs={}))
	    else:
	        form = OfferingBasicsForm()
	else:
	    form = OfferingBasicsForm()
	
	return render_to_response("planning/edit_courses.html",{'form':form, 'plan':plan, 'planned_courses_list':planned_courses_list},context_instance=RequestContext(request))

	
@requires_role('PLAN')
def delete_course_from_plan(request, course_id, plan_id):
	
	course = PlannedOffering.objects.get(pk = course_id)
	course.delete()
	
	semester_plan = get_object_or_404(SemesterPlan, pk = plan_id)
	semester = semester_plan.semester.name


	messages.add_message(request, messages.SUCCESS, 'Course Removed Successfully.')
	return HttpResponseRedirect(reverse(edit_courses, kwargs={'semester':semester, 'plan_slug':semester_plan.slug}))

@requires_role('PLAN')
def assign_instructors(request, semester, plan_slug):
	semester_plan = get_object_or_404(SemesterPlan, semester__name=semester, slug=plan_slug)
	
	# build list of offerings with their forms
	offerings = []
	for o in semester_plan.plannedoffering_set.all():
	    data = {}
	    data['offering'] = o
	    form = OfferingInstructorForm(instance=o)
	    choices = [(tc.instructor.userid, tc.instructor.name()) for tc in TeachingCapability.objects.filter(course=o.course)]
	    form.fields['instructor'].choices = [(None, u'\u2014')] + choices
	    data['form'] = form
	    offerings.append(data)
	
	return render_to_response("planning/assign_instructors.html",{'semester_plan': semester_plan, 'offerings': offerings},context_instance=RequestContext(request))
	
@requires_role('PLAN')
def submit_assigned_instructors(request, semester, plan_slug, offering_id):
	semester_plan = get_object_or_404(SemesterPlan, semester__name=semester, slug=plan_slug)
	course = get_object_or_404(PlannedOffering, pk=offering_id, plan=semester_plan)
	
	instructor_id = request.POST['instructor']
	assigned_instructor = get_object_or_404(Person, userid = instructor_id)
	
	if course.instructor:
		pre_instructor = course.instructor
	else:
		pre_instructor = None
	
	course.instructor = assigned_instructor
	course.save()
	
	intention_count = PlannedOffering.objects.filter(plan = semester_plan, instructor = assigned_instructor).count()	
	if TeachingIntention.objects.filter(semester = semester_plan.semester, instructor = assigned_instructor):
		teaching_intentions = TeachingIntention.objects.filter(semester = semester_plan.semester, instructor = assigned_instructor)
		teaching_intention = teaching_intentions[0]
		teaching_intention_count = teaching_intention.count
	else:
		teaching_intentions = None
		teaching_intention_count = 0
	
	#if teaching_intentions.count()==1:
	#	teaching_intention = teaching_intentions[0]
	
		if intention_count >= teaching_intention_count:
			teaching_intention.intentionfull = True
			teaching_intention.save()
		else:
			teaching_intention.intentionfull = False
			teaching_intention.save()

			
	if pre_instructor != None:
		pre_intention_count = PlannedOffering.objects.filter(plan = semester_plan, instructor = pre_instructor).count()
		pre_teaching_intention = TeachingIntention.objects.get(semester = semester_plan.semester, instructor = pre_instructor)
			
		if pre_intention_count >= pre_teaching_intention.count:
			pre_teaching_intention.intentionfull = True
			pre_teaching_intention.save()
		else:
			pre_teaching_intention.intentionfull = False
			pre_teaching_intention.save()
					
	messages.add_message(request, messages.SUCCESS, 'Instructor Assinged Successfully.')
	return HttpResponseRedirect(reverse(assign_instructors, kwargs={'semester':semester_plan.semester.name, 'plan_slug':semester_plan.slug}))
	#return HttpResponse('pre_instructor')
	
@requires_role('PLAN')
def activate_plan(request, plan_id):

	semester_plan = get_object_or_404(SemesterPlan, pk = plan_id)

	semester_plan.active = True
	semester_plan.save()

	messages.add_message(request, messages.SUCCESS, 'Plan Activated Successfully.')
	return HttpResponseRedirect(reverse(admin_index))
	
@requires_role('PLAN')
def inactivate_plan(request, plan_id):

	semester_plan = get_object_or_404(SemesterPlan, pk = plan_id)

	semester_plan.active = False
	semester_plan.save()

	messages.add_message(request, messages.SUCCESS, 'Plan Inactivated Successfully.')
	return HttpResponseRedirect(reverse(admin_index))

@requires_role('PLAN')
def delete_plan(request, semester, plan_slug):
	plan = get_object_or_404(SemesterPlan, semester__name=semester, slug=plan_slug)
	if request.method == 'POST':
	    plan.delete()
	    
	    #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("deleted course plan %s in %s") % (plan.name, plan.semester),
                  related_object=request.user)
            l.save()

	    messages.add_message(request, messages.SUCCESS, 'Plan Deleted.')
	return HttpResponseRedirect(reverse(admin_index))
		

#********************************************Deleted Functions************************************************************
#@requires_role('PLAN')
#def add_courses_to_plan(request, userid, plan_id):
	
#	semester_plan = get_object_or_404(SemesterPlan, pk = plan_id)
	
#	course_number = request.POST['offering_courses']
#	course = get_object_or_404(Course, number = course_number)
	
#	campus = request.POST['campus']
#	component = request.POST['component']
#	section = request.POST['section']
	
#	added_course_to_plan = PlannedOffering(plan = semester_plan, course = course, campus = campus, component = component, section = section)
#	added_course_to_plan.save()

#	messages.add_message(request, messages.SUCCESS, 'Course Added Successfully.')
#	return HttpResponseRedirect(reverse(edit_courses, kwargs={'userid':userid, 'plan_id':plan_id}))
#********************************************Deleted Functions************************************************************





