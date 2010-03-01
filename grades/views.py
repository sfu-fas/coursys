from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from coredata.models import Member, CourseOffering, Person, Role
from courselib.auth import requires_course_by_slug, requires_course_staff_by_slug, is_course_staff_by_slug
from grades.models import ACTIVITY_STATUS, FLAGS, all_activities_filter, \
                        NumericActivity, LetterActivity, NumericGrade, LetterGrade, ACTIVITY_TYPES
from grades.forms import NumericActivityForm, LetterActivityForm, FORMTYPE
from grades.models import *
from django.forms.util import ErrorList


@login_required
def index(request):
    # TODO: should distinguish student/TA/instructor roles in template
    userid = request.user.username
    memberships = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=userid) \
            .select_related('offering','person','offering__semester')
    return render_to_response("grades/index.html", {'memberships': memberships}, context_instance=RequestContext(request))
    
FROMPAGE = {'course': 'course', 'activityinfo': 'activityinfo'}
@requires_course_by_slug
def course(request, course_slug):
    """
    Course front page
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = course.activity_set.all()
    is_course_staff = is_course_staff_by_slug(request.user, course_slug)
    context = {'course': course, 'activities': activities, 'is_course_staff':is_course_staff, 'from_page': FROMPAGE['course']}
    return render_to_response("grades/course.html", context,
                              context_instance=RequestContext(request))
    
class _StudentGradeInfo:
    """
    Object holding student grade info for the 'activity_info' page 
    """
    def __init__(self, name, emplid, grade_status, grade):
        self.name = name
        self.emplid = emplid
        self.grade_status = grade_status
        self.grade = grade
        
def _create_StudentGradeInfo_list(course, activity):
    """
    Return a _StudentGradeInfo list which contains all the enrolled students' grade information in a course activity
    """
    if not [activity for activity_type in ACTIVITY_TYPES if isinstance(activity, activity_type)]:
        return
    if not isinstance(course, CourseOffering):
        return
    
    # verify if the course contains the activity
    if not all_activities_filter(slug=activity.slug, offering=course):
        return
    student_list = course.members.filter(person__role='STUD')
    student_grade_info_list = []
    for student in student_list:
        if isinstance(activity, NumericActivity):
            try:
                numeric_grade = NumericGrade.objects.get(activity=activity, member__person=student)
                student_grade_status = numeric_grade.get_flag_display()
                student_grade = str(numeric_grade.value) + '/' + str(activity.max_grade)
            except NumericGrade.DoesNotExist:
                student_grade_status = FLAGS['NOGR']
                student_grade = 'N/A'
        elif isinstance(activity, LetterActivity):
            try:
                letter_grade = LetterGrade.objects.get(activity=activity, member__person=student)
                student_grade_status = letter_grade.get_flag_display()
                student_grade = letter_grade.letter_grade
            except LetterGrade.DoesNotExist:
                student_grade_status = FLAGS['NOGR']
                student_grade = 'N/A'
        student_grade_info_list.append(_StudentGradeInfo(student.first_name + ' ' +
                                                            student.middle_name + ' ' +
                                                            student.last_name, student.emplid,
                                                            student_grade_status, student_grade))
    return student_grade_info_list

@requires_course_staff_by_slug
def activity_info(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)
    if (len(activities) == 1):
        activity = activities[0]
        student_grade_info_list = _create_StudentGradeInfo_list(course, activity)
        context = {'course': course, 'activity': activity, 'student_grade_info_list': student_grade_info_list, 'from_page': FROMPAGE['activityinfo']}
        return render_to_response('grades/activity_info.html', context, context_instance=RequestContext(request))
    else:
        raise Http404

@requires_course_staff_by_slug
def add_numeric_activity(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    
    if request.method == 'POST': # If the form has been submitted...
        form = NumericActivityForm(request.POST) # A form bound to the POST data
        form.activate_addform_validation(course_slug)
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
        form = NumericActivityForm()
    context = {'course': course, 'form': form, 'form_type': FORMTYPE['add']}
    return render_to_response('grades/numeric_activity_form.html', context, context_instance=RequestContext(request))

def _create_activity_formdatadict(activity):
    if not [activity for activity_type in ACTIVITY_TYPES if isinstance(activity, activity_type)]:
        return
    data = dict()
    data['name'] = activity.name
    data['short_name'] = activity.short_name
    data['status'] = activity.status
    data['due_date'] = activity.due_date
    data['percent'] = activity.percent
    data['position'] = activity.position
    if hasattr(activity, 'max_grade'):
        data['max_grade'] = activity.max_grade
    return data

def _populate_activity_from_formdata(activity, data):
    if not [activity for activity_type in ACTIVITY_TYPES if isinstance(activity, activity_type)]:
        return
    if data.has_key('name'):
        activity.name = data['name']
    if data.has_key('short_name'):
        activity.short_name = data['short_name']
    if data.has_key('status'):
        activity.status = data['status']
    if data.has_key('due_date'):
        activity.due_date = data['due_date']
    if data.has_key('percent'):
        activity.percent = data['percent']
    if data.has_key('max_grade'):
        activity.max_grade = data['max_grade']

@requires_course_staff_by_slug
def edit_activity(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)
    if (len(activities) == 1):
        activity = activities[0]
        
        from_page = request.GET['from_page']
        if from_page == None:
            from_page = FROMPAGE['course']
        
        if request.method == 'POST': # If the form has been submitted...
            if isinstance(activity, NumericActivity):
                form = NumericActivityForm(request.POST) # A form bound to the POST data
                form.activate_editform_validation(course_slug, activity_slug)
            if isinstance(activity, LetterActivity):
                form = LetterActivityForm(request.POST) # A form bound to the POST data
                form.activate_editform_validation(course_slug, activity_slug)
            if form.is_valid(): # All validation rules pass
                _populate_activity_from_formdata(activity, form.cleaned_data)
                activity.save()
                print from_page
                if from_page == FROMPAGE['course']:
                    return HttpResponseRedirect(reverse('grades.views.course', kwargs={'course_slug': course_slug}))
                elif from_page == FROMPAGE['activityinfo']:
                    return HttpResponseRedirect(reverse('grades.views.activity_info',
                                                        kwargs={'course_slug': course_slug, 'activity_slug': activity_slug}))
        else:
            datadict = _create_activity_formdatadict(activity)
            if isinstance(activity, NumericActivity):
                form = NumericActivityForm(datadict)
            elif isinstance(activity, LetterActivity):
                form = LetterActivityForm(datadict)
        if isinstance(activity, NumericActivity):
            context = {'course': course, 'activity': activity, 'form': form, 'form_type': FORMTYPE['edit'], 'from_page': from_page}
            return render_to_response('grades/numeric_activity_form.html', context, context_instance=RequestContext(request))
        elif isinstance(activity, LetterActivity):
            context = {'course': course, 'activity': activity, 'form': form, 'form_type': FORMTYPE['edit'], 'from_page': from_page}
            return render_to_response('grades/letter_activity_form.html', context, context_instance=RequestContext(request))
        
    else:
        raise Http404
    

    
@requires_course_staff_by_slug
def add_letter_activity(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    
    if request.method == 'POST': # If the form has been submitted...
        form = LetterActivityForm(request.POST) # A form bound to the POST data
        form.activate_addform_validation(course_slug)
        if form.is_valid(): # All validation rules pass
            # Todo: Need validation for already existed activity
            LetterActivity.objects.create(name=form.cleaned_data['name'],
                                           short_name=form.cleaned_data['short_name'],
                                           status=form.cleaned_data['status'],
                                            due_date=form.cleaned_data['due_date'],
                                            percent=form.cleaned_data['percent'],
                                            offering=course, position=1)
            return HttpResponseRedirect(reverse('grades.views.course',
                                                kwargs={'course_slug': course_slug}))
    else:
        form = LetterActivityForm()
    activities = course.activity_set.all()
    context = {'course': course, 'form': form, 'form_type': FORMTYPE['add']}
    return render_to_response('grades/letter_activity_form.html', context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def delete_activity_review(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(slug=activity_slug)
    if (len(activities) == 1):
        context = {'course': course, 'activity': activities[0]}
        return render_to_response('grades/delete_activity_review.html', context, context_instance=RequestContext(request))
    else:
        raise Http404

@requires_course_staff_by_slug
def delete_activity_confirm(request, course_slug, activity_slug):
    activity = get_object_or_404(Activity, slug=activity_slug)
    activity.delete()
    return HttpResponseRedirect(reverse('grades.views.course', kwargs={'course_slug': course_slug}))

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

