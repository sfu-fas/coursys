from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.template import RequestContext
from coredata.models import Member, CourseOffering, Person
from discipline.models import *
from discipline.forms import *
from courselib.auth import requires_course_staff_by_slug, NotFoundResponse


@requires_course_staff_by_slug
def index(request, course_slug):
    """
    List of cases for the course
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    cases = DisciplineCase.objects.filter(student__offering=course)
    groups = DisciplineGroup.objects.filter(offering=course)
    
    context = {'course': course, 'cases': cases, 'groups': groups}
    return render_to_response("discipline/index.html", context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def newgroup(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    
    if request.method == 'POST':
        form = DisciplineGroupForm(request.POST)
        group = form.save(commit=False)
        group.offering = course
        group.save()
        form.save_m2m()
        print ">>>", group

    else:
        form = DisciplineGroupForm()

    form.fields['students'].choices = [(m.person.userid, m.person.sortname()) for m in
            Member.objects.filter(offering=course, role="STUD").select_related('person')]
    context = {'course': course, 'form': form, 'group': True}
    return render_to_response("discipline/new.html", context, context_instance=RequestContext(request))
    #return _new(request, course_slug, group=True)

@requires_course_staff_by_slug
def new(request, course_slug, group=False):
    return _new(request, course_slug, group=False)

def _new(request, course_slug, group):
    """
    Create new case or case group
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    if request.method == 'POST':
        if group:
            groupobj = DisciplineGroup(name=request.POST['name'], offering=course)
            groupobj.save()
        else:
            groupobj = None

        userids = request.POST.getlist('userid')
        for userid in userids:
            students = Member.objects.filter(offering=course, role="STUD", person__userid=userid)
            if len(students) != 1:
                return NotFoundResponse(request)
            student = students[0]
        
            case = DisciplineCase(student=student, group=groupobj)
            case.save()

        if group:
            return HttpResponseRedirect(reverse('discipline.views.showgroup', kwargs={'course_slug': course_slug, 'group_slug': groupobj.slug}))
        else:
            return HttpResponseRedirect(reverse('discipline.views.show', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))


    students = Member.objects.filter(offering=course, role="STUD")
    context = {'course': course, 'students': students, 'group': group}
    return render_to_response("discipline/new.html", context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def show(request, course_slug, case_slug):
    """
    Display current case status
    """

@requires_course_staff_by_slug
def showgroup(request, course_slug, group_slug):
    """
    Display current case status
    """

