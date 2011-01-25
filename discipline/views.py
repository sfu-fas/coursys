from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, get_object_or_404
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.contrib import messages
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
    student_choices = [
            (m.person.userid,
               "%s (%s, %s)" % (m.person.sortname(), m.person.emplid, m.person.userid))
            for m in
            Member.objects.filter(offering=course, role="STUD").select_related('person')]
    
    if request.method == 'POST':
        form = DisciplineGroupForm(offering=course, data=request.POST)
        form.fields['students'].choices = student_choices
        if form.is_valid():
            group = form.save()
            for userid in form.cleaned_data['students']:
                # create case for each student in the group
                student = Member.objects.get(offering=course, person__userid=userid)
                case = DisciplineCase(student=student, group=group)
                case.save()
            return HttpResponseRedirect(reverse('discipline.views.showgroup', kwargs={'course_slug': course_slug, 'group_slug': group.slug}))

    else:
        form = DisciplineGroupForm(offering=course)

    form.fields['students'].choices = student_choices
    context = {'course': course, 'form': form}
    return render_to_response("discipline/newgroup.html", context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def new(request, course_slug, group=False):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    student_choices = [
            (m.person.userid,
               "%s (%s, %s)" % (m.person.sortname(), m.person.emplid, m.person.userid))
            for m in
            Member.objects.filter(offering=course, role="STUD").select_related('person')]
    
    if request.method == 'POST':
        form = DisciplineCaseForm(offering=course, data=request.POST)
        form.fields['student'].choices = student_choices
        if form.is_valid():
            case = form.save()
            return HttpResponseRedirect(reverse('discipline.views.show', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))

    else:
        form = DisciplineCaseForm(offering=course)

    form.fields['student'].choices = student_choices
    context = {'course': course, 'form': form}
    return render_to_response("discipline/new.html", context, context_instance=RequestContext(request))

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
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCase, slug=case_slug, student__offering__slug=course_slug)
    
    context = {'course': course, 'case': case}
    return render_to_response("discipline/show.html", context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def showgroup(request, course_slug, group_slug):
    """
    Display current case status
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    group = get_object_or_404(DisciplineGroup, slug=group_slug, offering__slug=course_slug)
    print DisciplineCase.objects.filter(group=group)
    
    context = {'course': course, 'group': group}
    return render_to_response("discipline/showgroup.html", context, context_instance=RequestContext(request))

def _edit_case_info(request, course_slug, case_slug, field, FormClass, name):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    case = get_object_or_404(DisciplineCase, slug=case_slug, student__offering__slug=course_slug)
    if request.method == 'POST':
        form = FormClass(instance=case, data=request.POST)
        if form.is_valid():
            form.save()
            messages.add_message(request, messages.INFO, name+' updated.')
            return HttpResponseRedirect(reverse('discipline.views.show', kwargs={'course_slug': course_slug, 'case_slug': case.slug}))
    else:
        form = FormClass(instance=case)
    
    context = {'course': course, 'case': case, 'form': form}
    return render_to_response("discipline/edit_"+field+".html", context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def edit_intro(request, course_slug, case_slug):
    return _edit_case_info(request, course_slug, case_slug, "intro", CaseIntroForm, "Introductory sentence")

@requires_course_staff_by_slug
def edit_contact(request, course_slug, case_slug):
    pass

