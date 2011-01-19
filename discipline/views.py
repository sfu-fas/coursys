from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.template import RequestContext
from coredata.models import Member, CourseOffering, Person
from discipline.models import *
from courselib.auth import requires_course_staff_by_slug, NotFoundResponse


@requires_course_staff_by_slug
def index(request, course_slug):
    """
    List of cases for the course
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    cases = DisciplineCase.objects.filter(student__offering=course)
    
    context = {'course': course, 'cases': cases}
    return render_to_response("discipline/index.html", context, context_instance=RequestContext(request))


@requires_course_staff_by_slug
def new(request, course_slug):
    """
    Create new case
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    if request.method == 'POST':
        userid = request.POST['userid']
        students = Member.objects.filter(offering=course, role="STUD", person__userid=userid)
        if len(students) != 1:
            return NotFoundResponse(request)
        student = students[0]
        
        case = DisciplineCase(student=student)
        case.save()
        return HttpResponseRedirect(reverse('discipline.views.show', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))


    students = Member.objects.filter(offering=course, role="STUD")
    context = {'course': course, 'students': students}
    return render_to_response("discipline/new.html", context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def show(request, course_slug, case_slug):
    """
    Display current case status
    """

