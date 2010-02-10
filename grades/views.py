from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from coredata.models import Member, CourseOffering,Person,Role
from courselib.auth import requires_course_by_slug
from grades.models import ACTIVITY_STATUS
from grades.forms import NumericActivityForm, LetterActivityForm
from grades.models import *
from django.forms.util import ErrorList


@login_required
def index(request):
    # TODO: should distinguish student/TA/instructor roles in template
    userid = request.user.username
    memberships = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=userid) \
            .select_related('offering','person','offering__semester')
    return render_to_response("grades/index.html", {'memberships': memberships}, context_instance=RequestContext(request))
    
    
# Todo: Role authentication required
@requires_course_by_slug
def course(request, course_slug):
    """
    Course front page
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = course.activity_set.all()
    context = {'course': course, 'activities': activities}
    return render_to_response("grades/course.html", context,
                              context_instance=RequestContext(request))
    
@requires_course_by_slug
def add_numeric_activity(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    
    if request.method == 'POST': # If the form has been submitted...
        form = NumericActivityForm(course_slug, request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            NumericActivity.objects.create(name=form.cleaned_data['name'],
                                           short_name=form.cleaned_data['short_name'],
                                           status=form.cleaned_data['status'],
                                            due_date=form.cleaned_data['due_date'],
                                            percent=form.cleaned_data['percent'],
                                            max_grade=form.cleaned_data['max_grade'],
                                            offering=course, position=1)
            return HttpResponseRedirect(reverse('grades.views.course', kwargs={'course_slug': course_slug}))
    else:
        form = NumericActivityForm(course_slug)
    print form.fields['name'].required
    activities = course.activity_set.all()
    context = {'course': course, 'activities': activities, 'form': form}
    return render_to_response('grades/add_numeric_activity.html', context, context_instance=RequestContext(request))
    
@requires_course_by_slug
def add_letter_activity(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    
    if request.method == 'POST': # If the form has been submitted...
        form = LetterActivityForm(course_slug, request.POST) # A form bound to the POST data
        if form.is_valid(): # All validation rules pass
            # Todo: Need validation for already existed activity
            LetterActivity.objects.create(name=form.cleaned_data['name'],
                                           short_name=form.cleaned_data['short_name'],
                                           status=form.cleaned_data['status'],
                                            due_date=form.cleaned_data['due_date'],
                                            percent=form.cleaned_data['percent'],
                                            offering=course, position=1)
            return HttpResponseRedirect(reverse('grades.views.course', kwargs={'course_slug': course_slug}))
    else:
        form = LetterActivityForm(course_slug)
    activities = course.activity_set.all()
    context = {'course': course, 'activities': activities, 'form': form}
    return render_to_response('grades/add_letter_activity.html', context, context_instance=RequestContext(request))



@login_required
def student_view(request):
    student_id = request.user.username
    student = Person.objects.get(userid = student_id )
    enrollment= Member.objects.filter(person=student).exclude(role="DROP").filter(offering__graded=True)
    context ={'enrollment':enrollment,'student':student}    
    return render_to_response('grades/student_view.html', context,
                                  context_instance=RequestContext(request))

@requires_course_by_slug
def student_grade(request,course_slug):
    student_id = request.user.username
    student = Person.objects.get(userid = student_id )
    course = CourseOffering.objects.get(slug=course_slug)
    numerics = NumericActivity.objects.filter(offering = course)
    letters = LetterActivity.objects.filter(offering = course)
    context = {'student':student,'course': course, 'numerics': numerics,'letters':letters}
    return render_to_response("grades/student_grade.html", context,
                              context_instance=RequestContext(request))

