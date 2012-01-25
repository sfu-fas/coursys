from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404, render
from django.core.urlresolvers import reverse
from courselib.auth import requires_course_staff_by_slug, is_course_staff_by_slug, is_course_student_by_slug, ForbiddenResponse, NotFoundResponse
from ta.models import TUG
from coredata.models import *
from ta.forms import *

# TODO: Allow department admin to access these pages.  

@requires_course_staff_by_slug
def index_page(request, course_slug):
    if is_course_staff_by_slug(request, course_slug):
        return render(request, 'ta/index.html',{})
    else:
        return ForbiddenResponse(request)
        
@requires_course_staff_by_slug
def all_tugs(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    tas = Member.objects.filter(offering=course, role="TA")
    #If a TA is accessing, only his/her own TUG should be viewable
    if request.user.username in tas:
        tas.filter(person__userid=request.user.username)
    tugs = TUG.objects.filter(member=tas)        
    context = {'tas': tas, 
               'tugs': tugs,
                'course': course
                }
    
    return render(request, 'ta/all_tugs.html', context)

@requires_course_staff_by_slug    
def new_tug(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    if request.method == "POST":
        form = TUGForm(data=request.POST)
        if form.is_valid():
            tug = form.save(False)
            tug.save()
        return HttpResponseRedirect(reverse(all_tugs, args=[course.slug]))
    
    else:
        form = TUGForm(course)
        return render(request,'ta/new_tug.html',{'course':course, 'form':form})

@requires_course_staff_by_slug    
def view_tug(request, course_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    member = get_object_or_404(Member, offering=course, person__userid=userid)
    curr_user_role = Member.objects.get(person__userid=request.user.username,offering=course).role
    
    #If the currently logged in user is a TA for the course and is viewing a TUG for another TA, show forbidden message
    if(curr_user_role =="TA" and not userid==request.user.username ): 
        return ForbiddenResponse(request)
    else:
        course = get_object_or_404(CourseOffering, slug=course_slug)
        member = get_object_or_404(Member, offering=course, person__userid=userid)
        tug = TUG.objects.get(member=member)
        max_hours = tug.base_units * 42
        total_hours = 0 
        for field, params in tug.config.iteritems():
            if not field == 'other2':
                total_hours += params['total']
        
        context = {'tug': tug, 'ta':member, 'course':course, 'maxHours':max_hours, 'totalHours':total_hours}
        return render(request, 'ta/view_tug.html',context)

@requires_course_staff_by_slug
def edit_tug(request, course_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    member = get_object_or_404(Member, offering=course, person__userid=userid)
    tug = TUG.objects.get(member=member)
    if (request.method=="POST"):
        tug_form = TUGForm(request.POST)
    else:
        tug_form = TUGForm(instance=tug)
    context = {'course':course, 'ta':member.person, 'form': tug_form, 'tug':tug }
    
    return render(request, 'ta/edit_tug.html',context)
