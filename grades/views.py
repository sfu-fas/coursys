from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models.aggregates import Max
from coredata.models import Member, CourseOffering, Person, Role
from courselib.auth import requires_course_by_slug, requires_course_staff_by_slug, is_course_staff_by_slug, is_course_student_by_slug
from grades.models import ACTIVITY_STATUS, all_activities_filter, Activity, \
                        NumericActivity, LetterActivity, ACTIVITY_TYPES
from grades.forms import NumericActivityForm, LetterActivityForm, FORMTYPE
from grades.models import *
from grades.utils import StudentActivityInfo, reorder_course_activities, create_StudentActivityInfo_list, \
                        ORDER_TYPE
from django.forms.util import ErrorList


FROMPAGE = {'course': 'course', 'activityinfo': 'activityinfo'}
ACTIVITY_TYPE = {'NG': 'Numeric Graded', 'LG': 'Letter Graded'} # for display purpose

@login_required
def course_info(request, course_slug):
    #if course staff
    if is_course_staff_by_slug(request.user, course_slug):
        return _course_info_staff(request, course_slug)
    #else course member
    elif is_course_student_by_slug(request.user, course_slug):
        return _course_info_student(request, course_slug)
    #else not found, return 403
    else:
        return HttpResponseForbidden()
    
#@requires_course_staff_by_slug
def _course_info_staff(request, course_slug):
    """
    Course front page
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(offering=course)
    
    order = None
    act = None
    if request.GET.has_key('order'):
        order = request.GET['order']
    if request.GET.has_key('act'):
        act = request.GET['act']
    if order:
        reorder_course_activities(activities, act, order)
        return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course_slug}))

    activities_info = []
    for activity in activities:
        if isinstance(activity, NumericActivity):
            activities_info.append({'activity':activity, 'type':ACTIVITY_TYPE['NG']})            
        elif isinstance(activity, LetterActivity):
            activities_info.append({'activity':activity, 'type':ACTIVITY_TYPE['LG']})
    
    context = {'course': course, 'activities_info': activities_info, 'from_page': FROMPAGE['course'],
               'order_type': ORDER_TYPE}
    return render_to_response("grades/course_info_staff.html", context,
                              context_instance=RequestContext(request))
    

#@requires_course_student_by_slug
def _course_info_student(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(offering=course, status__in=['RLS', 'URLS'])
    
    activityinfo_list = []
    for activity in activities:
        activityinfo_list.append(create_StudentActivityInfo_list(course, activity,
                                                                student=Person.objects.get(userid=request.user.username))[0].append_activity_stat())
    context = {'course': course, 'activityinfo_list': activityinfo_list, 'from_page': FROMPAGE['course']}
    return render_to_response("grades/course_info_student.html", context,
                              context_instance=RequestContext(request))

@requires_course_staff_by_slug
def activity_info(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)
    if (len(activities) == 1):
        activity = activities[0]
        id = None
        if request.GET.has_key('id'):
            id = request.GET['id']
        if not id:
            student_grade_info_list = create_StudentActivityInfo_list(course, activity)
            if isinstance(activity, NumericActivity):
                activity_type = ACTIVITY_TYPE['NG']
            elif isinstance(activity, LetterActivity):
                activity_type = ACTIVITY_TYPE['LG']
            context = {'course': course, 'activity_type': activity_type, 'activity': activity, 'student_grade_info_list': student_grade_info_list, 'from_page': FROMPAGE['activityinfo']}
            return render_to_response('grades/activity_info.html', context, context_instance=RequestContext(request))
        else:
            student = get_object_or_404(Person, id=id)
            student_grade_info = create_StudentActivityInfo_list(course, activity, student)[0]
            context = {'course': course, 'activity': activity, 'student_grade_info': student_grade_info}
            return render_to_response('grades/student_grade_info.html', context, context_instance=RequestContext(request))
    else:
        raise Http404

@requires_course_staff_by_slug
def add_numeric_activity(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    
    if request.method == 'POST': # If the form has been submitted...
        form = NumericActivityForm(request.POST) # A form bound to the POST data
        form.activate_addform_validation(course_slug)
        if form.is_valid(): # All validation rules pass
            try:
                aggr_dict = Activity.objects.filter(offering=course).aggregate(Max('position'))
                if not aggr_dict['position__max']:
                    position = 1
                else:
                    position = aggr_dict['position__max'] + 1
                NumericActivity.objects.create(name=form.cleaned_data['name'],
                                                short_name=form.cleaned_data['short_name'],
                                                status=form.cleaned_data['status'],
                                                due_date=form.cleaned_data['due_date'],
                                                percent=form.cleaned_data['percent'],
                                                max_grade=form.cleaned_data['max_grade'],
                                                offering=course, position=position)
            except Exception:
                raise Http404
            return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course_slug}))
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
                    return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course_slug}))
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
            try:
                aggr_dict = Activity.objects.filter(offering=course).aggregate(Max('position'))
                if not aggr_dict['position__max']:
                    position = 1
                else:
                    position = aggr_dict['position__max'] + 1
                LetterActivity.objects.create(name=form.cleaned_data['name'],
                                                short_name=form.cleaned_data['short_name'],
                                                status=form.cleaned_data['status'],
                                                due_date=form.cleaned_data['due_date'],
                                                percent=form.cleaned_data['percent'],
                                                offering=course, position=position)
            except Exception:
                raise Http404
            return HttpResponseRedirect(reverse('grades.views.course_info',
                                                kwargs={'course_slug': course_slug}))
    else:
        form = LetterActivityForm()
    activities = course.activity_set.all()
    context = {'course': course, 'form': form, 'form_type': FORMTYPE['add']}
    return render_to_response('grades/letter_activity_form.html', context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def delete_activity_review(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(offering=course, slug=activity_slug)
    if (len(activities) == 1):
        activity = activities[0]
        if isinstance(activity, NumericActivity):
                activity_type = ACTIVITY_TYPE['NG']
        elif isinstance(activity, LetterActivity):
            activity_type = ACTIVITY_TYPE['LG']
        context = {'course': course, 'activity_type': activity_type, 'activity': activities[0]}
        return render_to_response('grades/delete_activity_review.html', context, context_instance=RequestContext(request))
    else:
        raise Http404

@requires_course_staff_by_slug
def delete_activity_confirm(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = list(course.activity_set.all())
    activity_found = False
    for i in range(0, len(activities)):
        if activities[i].slug == activity_slug:
            activity_found = True
            try:
                activities[i].delete()
            except Exception:
                raise Http404
            for j in range(len(activities) - 1, i, -1):
                activities[j].position = activities[j-1].position
                activities[j].save()
            break
    if not activity_found:
        raise Http404
    return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course_slug}))