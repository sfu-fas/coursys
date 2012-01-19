from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404, render
from courselib.auth import requires_course_staff_by_slug, is_course_staff_by_slug, is_course_student_by_slug, ForbiddenResponse, NotFoundResponse
from ta.models import TUG
from coredata.models import *

@requires_course_staff_by_slug
def index_page(request, course_slug):
    if is_course_staff_by_slug(request, course_slug):
        return render_to_response('ta/index.html',{})
    else:
        return ForbiddenResponse(request)
        
@requires_course_staff_by_slug
def all_tugs(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    tas = Member.objects.filter(offering=course, role="TA")
    
    context = {'tas': tas, 'course': course.name, 'course_slug': course_slug}
    return render(request, 'ta/all_tugs.html', context)

@requires_course_staff_by_slug    
def new_tug(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    if request.method == "POST":
        return HttpResponseRedirect(reverse('ta.views.all_tugs', kwargs={}))
    
    else:
        return render(request,'ta/new_tug.html',{'course':course})

@requires_course_staff_by_slug    
def view_tug(request, course_slug, userid):
    return HttpResponse('View TUG page')

@requires_course_staff_by_slug
def edit_tug(request, course_slug, userid):
    return HttpResponse('Edit TUG page')
