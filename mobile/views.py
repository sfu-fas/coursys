import shlex
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.views.decorators.gzip import gzip_page
from courselib.auth import *
from grades.models import ACTIVITY_STATUS, all_activities_filter, Activity
from groups.models import *
from submission.models import GroupSubmission, StudentSubmission
from datetime import datetime
from submission.models import *

from dashboard.views import _get_memberships, _get_news_list, _get_roles

@login_required
@gzip_page
def index(request):
    userid = request.user.username
    memberships = _get_memberships(userid)
    news_list = _get_news_list(userid, 1)
    roles = _get_roles(userid)

    context = {'memberships': memberships ,'news_list': news_list, 'roles': roles}
    return render_to_response('mobile/dashboard.html',
        context, context_instance=RequestContext(request))

@login_required
@gzip_page
def course_info(request,course_slug):
    if is_course_student_by_slug(request, course_slug):
        return _course_info_student(request, course_slug)
    elif is_course_staff_by_slug(request, course_slug):
        return _course_info_staff(request, course_slug)
    else:
        return ForbiddenResponse(request)

def _course_info_student(request, course_slug):
    """
    Course front page for student
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(offering=course)
    student = Member.objects.get(offering=course, person__userid=request.user.username, role='STUD')
    activities_info = []
    for activity in activities:
        submission, submitted_components = get_current_submission(student, activity)
        if submission == None:
            submitted = "No"
        else:
            submitted = "yes"
        activities_info.append({'activity':activity, 'grade': activity.display_grade_student(student.person), 'submitted' : submitted})
    context = {'course': course, 'activities_info':activities_info}
    return render_to_response('mobile/course_info_student.html', context, context_instance=RequestContext(request))

def _course_info_staff(request, course_slug):
    """
    Course front page for staff
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(offering=course)

    activities_info = []
    for activity in activities:
        count = 0 # group/student count, based on activity type
        student_count = 0 # count of all students
        sub_count= 0 # count of submissions
        grade_count = 0 # count of graded students
        
        if activity.due_date and activity.due_date < datetime.now():
            passdue = True
        else:
            passdue = False

        # count number of students
        students = Member.objects.filter(role="STUD", offering=activity.offering).select_related('person')
        for student in students:
            student_count = student_count + 1
            if len(StudentSubmission.objects.filter(member=student))!=0:
                sub_count = sub_count + 1
        
        # if group, count group submission
        if activity.group:
            groups = Group.objects.filter(courseoffering=course)
            for group in groups:
                # count how many groups have submitted for this activity
                groupMembers = GroupMember.objects.filter(group=group, activity=activity, confirmed=True)
                if(len(groupMembers)!=0):
                    count = count + 1
                    if len(GroupSubmission.objects.filter(group=group, activity=activity))!=0:
                        sub_count = sub_count + 1
        else:
            count = student_count

        # count number of graded students
        if activity.is_numeric():
            grades_list = activity.numericgrade_set.filter().select_related('member__person', 'activity')
        else:
            grades_list = activity.lettergrade_set.filter().select_related('member__person', 'activity')
        grade_count = len(grades_list)

        activities_info.append({'activity':activity, 'count':count,'sub_count':sub_count, 'student_count':student_count,
                            'grade_count': grade_count, 'passdue':passdue})
        

    context = {'course': course, 'activities_info': activities_info}
    return render_to_response("mobile/course_info_staff.html", context,
                              context_instance=RequestContext(request))


@login_required
@gzip_page
def activity_info(request, course_slug, activity_slug):
    if is_course_student_by_slug(request, course_slug):
        return _activity_info_student(request, course_slug, activity_slug)
    elif is_course_staff_by_slug(request, course_slug):
        return _activity_info_staff(request, course_slug, activity_slug)

@login_required
@gzip_page
def _activity_info_student(request, course_slug, activity_slug):
    return HttpResponse('Student View')

@login_required
@gzip_page
def _activity_info_staff(request, course_slug, activity_slug):
    """
    activity detail page
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)
    if len(activities) != 1:
        return NotFoundResponse(request)

    activity = activities[0]

    context = {'course': course, 'activity': activity}
    return render_to_response("mobile/activity_info_staff.html", context,
                            context_instance=RequestContext(request))

@login_required
@gzip_page
def student_activity_search(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)
    if len(activities) != 1:
        return NotFoundResponse(request)

    activity = activities[0]

    q = request.GET.get('q')
    q = q.encode('ascii','ignore')
    print q
    try:
        keywords = shlex.split(q)
    except:
        return HttpResponse("Please check your input.")
    if keywords == None :
        context = {'course': course, 'activity': activity}
    else:
        students = Member.objects.filter(role="STUD", offering=activity.offering).select_related('person')
        for kw in keywords:
            new_list = []
            for s in students:
                ss = s.person.last_name+\
                            s.person.middle_name+\
                            s.person.first_name+\
                            s.person.userid+\
                            str(s.person.emplid)
                if kw in ss:
                    new_list.append(s)
            students = new_list[:]


    context = {'course': course, 'activity': activity, 'student_list':students}
    return render_to_response("mobile/search_student.html", context,
                            context_instance=RequestContext(request))

def student_activity_info(request, course_slug, activity_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)
    if len(activities) != 1:
        return NotFoundResponse(request)
    activity = activities[0]
    student = Member.objects.get(offering=course, person__userid=userid, role='STUD')
    return HttpResponse(student.person.last_name)
    