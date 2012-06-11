from planning.models import *
from planning.forms import *
from courselib.auth import requires_instructor
from courselib.auth import requires_role
from django.db.models import Q
from coredata.models import Person, Role, Semester, Member, Course, CourseOffering, COMPONENT_CHOICES, CAMPUS_CHOICES, WEEKDAY_CHOICES 
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
from dashboard.models import *

@requires_instructor
def instructor_index(request):
    instructor = get_object_or_404(Person, userid=request.user.username)
    capability_list = TeachingCapability.objects.filter(instructor=instructor).order_by('course')
    intention_list = TeachingIntention.objects.filter(instructor =instructor).order_by('semester')

    return render_to_response("planning/instructor_index.html", {'capability_list':capability_list, 'intention_list':intention_list}, context_instance=RequestContext(request))


@requires_instructor
def edit_capability(request):
    instructor = get_object_or_404(Person, userid=request.user.username)
    capability_list = TeachingCapability.objects.filter(instructor=instructor).order_by('course')
    unit_choices = request.units
    possible_courses = [(c.id, c.full_name()) for c in Course.objects.filter(courseoffering__owner__in=unit_choices).distinct()]

    if request.method == 'POST':
        form = CapabilityForm(request.POST)
        form.fields['course'].choices = possible_courses

        form.instructor_id = instructor.id
        if form.is_valid():
            capability = form.save()
            
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                      description=("Added teaching capability %s") % (capability.course.full_name()),
                      related_object=capability)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Added teaching capability %s.' % (capability.course.full_name()))
            return HttpResponseRedirect(reverse('planning.views.edit_capability', kwargs={}))
    else:
        form = CapabilityForm(initial={'instructor':instructor})
        form.fields['course'].choices = possible_courses
    
    return render_to_response("planning/add_capability.html",{'capability_list': capability_list, 'form':form}, context_instance=RequestContext(request))


@requires_instructor
def edit_intention(request):
    instructor = get_object_or_404(Person, userid=request.user.username)
    semester_list = Semester.objects.filter(start__gt=datetime.now())
    intention_list = TeachingIntention.objects.filter(instructor=instructor).order_by('semester')
    
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
        form.fields['semester'].choices = [(s.pk, s) for s in semester_list]
    
    return render_to_response("planning/add_intention.html",{'form':form, 'intention_list':intention_list}, context_instance=RequestContext(request))


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


@requires_instructor
def delete_capability(request, course_id):
    instructor = get_object_or_404(Person, userid=request.user.username)
    teaching_capability = get_object_or_404(TeachingCapability, pk=course_id, instructor=instructor)
    course = get_object_or_404(Course, teachingcapability=teaching_capability)
    messages.add_message(request, messages.SUCCESS, '%s %s removed from teachable courses.' % (course.subject, course.number))
    teaching_capability.delete()

    return HttpResponseRedirect(reverse(edit_capability, kwargs={}))


@requires_instructor
def delete_intention(request, semester):
    instructor = get_object_or_404(Person, userid=request.user.username)
    teaching_intention = get_object_or_404(TeachingIntention, semester__name=semester, instructor=instructor)
    semester = get_object_or_404(Semester, name=semester)
    messages.add_message(request, messages.SUCCESS, '%s plan removed.' % (semester))
    teaching_intention.delete()

    return HttpResponseRedirect(reverse(edit_intention, kwargs={}))


@requires_role('PLAN')
def admin_index(request):
    userid = request.user.username
    plan_list = SemesterPlan.objects.filter(unit__in=request.units).order_by('semester')

    return render_to_response("planning/admin_index.html",{'userid':userid, 'plan_list':plan_list}, context_instance=RequestContext(request))


@requires_role('PLAN')
def add_plan(request):
    unit_choices = [(u.id, unicode(u)) for u in request.units]

    if request.method == 'POST':
        form = PlanBasicsForm(request.POST)
        if form.is_valid():
            semester = form.cleaned_data['semester']
            other_plans = SemesterPlan.objects.filter(semester = semester, active = True)
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
    
    return render_to_response("planning/add_plan.html",{'form':form},context_instance=RequestContext(request))


@requires_role('PLAN')
def copy_plan(request):
    if request.method == 'POST':
        form = CopyPlanForm(request.POST)
        if form.is_valid():
            #plan = form.save()
            copied_plan_name = form.cleaned_data['copy_plan_from']
            copied_plan = SemesterPlan.objects.get(name=copied_plan_name)       
            copied_courses = PlannedOffering.objects.filter(plan=copied_plan).order_by('course')
            other_plans = SemesterPlan.objects.filter(semester = copied_plan.semester, active = True).exclude(pk = copied_plan.id)
            plan = form.save()
        
            for i in copied_courses:
                added_course = PlannedOffering(plan=plan, course=i.course, section=i.section, component=i.component, campus=i.campus, enrl_cap=i.enrl_cap)                
                added_course.save()

            l = LogEntry(userid=request.user.username,
                      description=("Copied course plan %s in %s") % (plan.name, plan.semester),
                      related_object=plan)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'New plan "%s" created.' % (plan.name))
            return HttpResponseRedirect(reverse('planning.views.admin_index', kwargs={}))
    else:
        form = CopyPlanForm()

    return render_to_response("planning/copy_plan.html",{'form':form},context_instance=RequestContext(request))


@requires_role('PLAN')
def edit_plan(request, semester, plan_slug):
    plan = get_object_or_404(SemesterPlan, semester__name=semester, slug=plan_slug)
    other_plans = SemesterPlan.objects.filter(semester = plan.semester, active = True).exclude(pk = plan.id)
    if request.method == 'POST':
        form = PlanBasicsForm(request.POST, instance=plan)
        if form.is_valid():
            plan = form.save()
            
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                      description=("Modified course plan %s in %s") % (plan.name, plan.semester),
                      related_object=plan)
            l.save()
                
            messages.add_message(request, messages.SUCCESS, 'Plan "%s" updated.' % (plan.name))
            return HttpResponseRedirect(reverse('planning.views.admin_index', kwargs={}))
    else:
            form = PlanBasicsForm(instance=plan)
    
    return render_to_response("planning/edit_plan.html",{'form':form, 'plan':plan},context_instance=RequestContext(request))


@requires_role('PLAN')
def edit_courses(request, semester, plan_slug):
    plan = get_object_or_404(SemesterPlan, semester__name=semester, slug=plan_slug)
    planned_offerings_list = PlannedOffering.objects.filter(plan=plan)
    courses = [(c.id, c.full_name()) for c in Course.objects.filter(courseoffering__owner=plan.unit).distinct()]

    if request.method == 'POST':
        form = OfferingBasicsForm(request.POST)
        form.fields['course'].choices = courses
        form2 = form
        if form.is_valid():
            offering = form.save(commit=False)
            offering.plan = plan
            num_of_lab = form.cleaned_data['lab_sections']
            offering.save()
            form.save_m2m()

            num_of_lab = int(num_of_lab)
            if num_of_lab != 0:
                for i in range(num_of_lab):
                    course = form.cleaned_data['course']
                    section = form.cleaned_data['section'][:2] + "%02i" % (i+1)    
                    component = "LAB"    
                    campus = form.cleaned_data['campus']
                    enrl_cap = form.cleaned_data['enrl_cap']

                    added_lab_section = PlannedOffering(plan=plan, course=course, section=section, component=component, campus=campus, enrl_cap=enrl_cap)
                    added_lab_section.save();

                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("added offering %s in %s") % (offering.course, offering.plan),
                      related_object=plan)
                l.save()
                    
                messages.add_message(request, messages.SUCCESS, 'Added course %s.' % (offering.course))
            else:
                form = OfferingBasicsForm()
                form.fields['course'].choices = courses
    else:
        form = OfferingBasicsForm()
        form.fields['course'].choices = courses
    
    return render_to_response("planning/edit_courses.html", {'form': form, 'plan': plan, 'planned_offerings_list': planned_offerings_list}, context_instance=RequestContext(request))

    
@requires_role('PLAN')
def delete_course_from_plan(request, course_id, plan_id):
    course = PlannedOffering.objects.get(pk = course_id)
    course.delete()
    
    semester_plan = get_object_or_404(SemesterPlan, pk = plan_id)
    semester = semester_plan.semester.name

    messages.add_message(request, messages.SUCCESS, 'Course removed successfully.')
    return HttpResponseRedirect(reverse(edit_courses, kwargs={'semester':semester, 'plan_slug':semester_plan.slug}))


@requires_role('PLAN')
def activate_plan(request, plan_id):
    semester_plan = get_object_or_404(SemesterPlan, pk=plan_id)

    semester_plan.active = True
    other_plans = SemesterPlan.objects.filter(semester=semester_plan.semester, active=True).exclude(pk=plan_id)
    other_plans = list(other_plans)

    semester_plan.save()
    
    messages.add_message(request, messages.SUCCESS, '%s Activated successfully.' % (semester_plan.name))
    for other_plan in other_plans:
        messages.add_message(request, messages.SUCCESS, '%s Inactivated successfully.' % (other_plan.name))

    return HttpResponseRedirect(reverse(admin_index))


@requires_role('PLAN')
def inactivate_plan(request, plan_id):
    semester_plan = get_object_or_404(SemesterPlan, pk = plan_id)

    semester_plan.active = False
    semester_plan.save()

    messages.add_message(request, messages.SUCCESS, '%s Inactivated successfully.' % (semester_plan.name))
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

    messages.add_message(request, messages.SUCCESS, 'Plan deleted.')
    return HttpResponseRedirect(reverse(admin_index))
 

@requires_role('PLAN')
def view_instructors(request, semester, plan_slug, planned_offering_slug):
    semester_plan = get_object_or_404(SemesterPlan, semester__name=semester, slug=plan_slug)
    planned_offering = get_object_or_404(PlannedOffering, slug=planned_offering_slug)

    all_instructors = Person.objects.filter(role__role__in=["FAC", "SESS", "COOP"], role__unit=semester_plan.unit)
    capable_instructors = all_instructors.filter(teachingcapability__course__plannedoffering=planned_offering)
    all_instructors = all_instructors.exclude(teachingcapability__course__plannedoffering=planned_offering)

    if request.method == 'POST':
        semester_plan = get_object_or_404(SemesterPlan, semester__name=semester, slug=plan_slug)
        course = get_object_or_404(PlannedOffering, slug=planned_offering_slug, plan=semester_plan)

        no_intention_note = "Added by planned administrator. Instructor posted no previous semester teaching plans."
        
        instructor_id = request.POST['instructor']
        if instructor_id == "None":
            pre_instructor = course.instructor
            course.instructor = None
            course.save()
            
            offering_section = course.section[0:2] # e.g. "D1"
            labs = PlannedOffering.objects.filter(plan=semester_plan, course=course.course, component__in=['LAB', 'TUT'], section__startswith=offering_section)
            for lab in labs:
                lab.instructor = None
                lab.save()

            pre_intention_count = PlannedOffering.objects.filter(plan=semester_plan, instructor=pre_instructor).count()
            pre_teaching_intention = TeachingIntention.objects.get(semester=semester_plan.semester, instructor=pre_instructor)
         
            if pre_teaching_intention.note == no_intention_note:
                pre_teaching_intention.delete()
            else:   
                pre_teaching_intention.intentionfull = (pre_intention_count >= pre_teaching_intention.count)
                pre_teaching_intention.save()

            messages.add_message(request, messages.SUCCESS, 'Instructor removed successfully.')
            return HttpResponseRedirect(reverse(edit_courses, kwargs={'semester':semester_plan.semester.name, 'plan_slug':semester_plan.slug}))       

        #instructor_id is not None
        assigned_instructor = get_object_or_404(Person, userid=instructor_id)
        
        if course.instructor:
            pre_instructor = course.instructor
        else:
            pre_instructor = None
        
        course.instructor = assigned_instructor
        course.save()

        offering_section = course.section[0:2] # e.g. "D1"
        labs = PlannedOffering.objects.filter(plan=semester_plan, course=course.course, component__in=['LAB', 'TUT'], section__startswith=offering_section)
        for lab in labs:
            lab.instructor = assigned_instructor
            lab.save()

        if pre_instructor != None:
            pre_intention_count = PlannedOffering.objects.filter(plan=semester_plan, instructor=pre_instructor).count()
            pre_teaching_intention = TeachingIntention.objects.get(semester=semester_plan.semester, instructor=pre_instructor)

            if pre_teaching_intention.note == no_intention_note:
                pre_teaching_intention.delete()
            else:
                pre_teaching_intention.intentionfull = (pre_intention_count >= pre_teaching_intention.count)
                pre_teaching_intention.save()
        
        intention_count = PlannedOffering.objects.filter(plan=semester_plan, instructor=assigned_instructor).count()    
        if TeachingIntention.objects.filter(semester=semester_plan.semester, instructor=assigned_instructor):
            teaching_intentions = TeachingIntention.objects.filter(semester=semester_plan.semester, instructor=assigned_instructor)
            teaching_intention = teaching_intentions[0]
        
            teaching_intention.intentionfull = (intention_count >= teaching_intentions.count)
            teaching_intention.save()

            messages.add_message(request, messages.SUCCESS, 'Instructor assinged successfully.')
            return HttpResponseRedirect(reverse(edit_courses, kwargs={'semester':semester_plan.semester.name, 'plan_slug':semester_plan.slug}))

        else:
            add_intention = TeachingIntention(instructor=assigned_instructor, semester=semester_plan.semester, count=1, intentionfull=True, note=no_intention_note)
            add_intention.save()
            messages.add_message(request, messages.WARNING, 'There is no intention for this instructor.')
            return HttpResponseRedirect(reverse(edit_courses, kwargs={'semester':semester_plan.semester.name, 'plan_slug':semester_plan.slug}))
    
    capable_instructors_list = []
    for i in capable_instructors:
        capable_instructors_list.append({
            'instructor': i,
            'intention': TeachingIntention.objects.filter(instructor=i).order_by('semester'),
            'teachable': TeachingCapability.objects.filter(instructor=i).order_by('course'),
            'current_courses': PlannedOffering.objects.filter(plan=semester_plan, instructor=i, component="LEC")
        })

    all_instructors_list = []
    for i in all_instructors:
        all_instructors_list.append({
            'instructor': i,
            'intention': TeachingIntention.objects.filter(instructor=i).order_by('semester'),
            'teachable': TeachingCapability.objects.filter(instructor=i).order_by('course'),
            'current_courses': PlannedOffering.objects.filter(plan=semester_plan, instructor=i, component="LEC")
        })
    
    return render_to_response("planning/view_instructors.html", {'semester_plan': semester_plan, 'capable_instructors_list': capable_instructors_list, 'all_instructors_list': all_instructors_list, 'planned_offering': planned_offering}, context_instance=RequestContext(request))


@login_required
def semester_plan_index(request):
    userid = request.user.username
    person = get_object_or_404(Person, userid=userid)
    roles = Role.objects.filter(person=person)

    admin = 0
    inst = 0

    for role in roles:
        if role.role == 'PLAN':
            admin = 1
        elif role.role == 'FAC' or role.role == 'SESS':
            inst = 1

    if admin == 1:
        plan_list = SemesterPlan.objects.filter(active=True, visibility__in=['ADMI', 'INST', 'ALL']).order_by('semester')
    elif inst == 1 and admin == 0:
        plan_list = SemesterPlan.objects.filter(active=True, visibility__in=['INST', 'ALL']).order_by('semester')
    elif admin == 0 and inst == 0:
        plan_list = SemesterPlan.objects.filter(active=True, visibility='ALL').order_by('semester')

    return render_to_response("planning/semester_plan_index.html",{'userid':userid, 'plan_list':plan_list},context_instance=RequestContext(request))


@login_required
def view_semester_plan(request, semester):
    plan = get_object_or_404(SemesterPlan, semester__name=semester, active=True)
    planned_courses_list = PlannedOffering.objects.filter(plan=plan)
        
    return render_to_response("planning/view_semester_plan.html",{'plan':plan, 'planned_courses_list':planned_courses_list},context_instance=RequestContext(request))