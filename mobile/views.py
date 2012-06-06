import shlex
from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.views.decorators.gzip import gzip_page
from courselib.auth import *
from coredata.models import Role
from grades.models import ACTIVITY_STATUS, all_activities_filter, Activity
from groups.models import *
from submission.models import GroupSubmission, StudentSubmission
from datetime import datetime
from submission.models import *
from grades.utils import generate_numeric_activity_stat,generate_letter_activity_stat

from dashboard.views import _get_memberships, _get_news_list

@login_required
@gzip_page
def index(request):
    userid = request.user.username
    memberships = _get_memberships(userid)
    news_list = _get_news_list(userid, 2)
    roles = Role.all_roles(userid)

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
    activities = [a for a in activities if a.status in ['RLS', 'URLS']]
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


def _activity_info_student(request, course_slug, activity_slug):
    # Course should have this number to student to display the activity statistics, including histogram
    STUD_NUM_TO_DISP_ACTSTAT = 10
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)
    if len(activities) != 1:
        return NotFoundResponse(request)
    activity = activities[0]
    if activity.status=="INVI":
        return NotFoundResponse(request)
    student = Member.objects.get(offering=course, person__userid=request.user.username, role='STUD')
    grade = (activity.GradeClass).objects.filter(activity=activity, member=student)
    if activity.status != "RLS" or not grade:
        # shouldn't display or nothing in database: create temporary nograde object for the template
        grade = (activity.GradeClass)(activity=activity, member=student, flag="NOGR")
    else:
        grade = grade[0]
        
    reason_msg = ''

    if activity.is_numeric():
       activity_stat = generate_numeric_activity_stat(activity)
    else:
       activity_stat = generate_letter_activity_stat(activity)

    if activity_stat is None or activity_stat.count < STUD_NUM_TO_DISP_ACTSTAT or activity.status!="RLS":
        if activity_stat is None or activity_stat.count < STUD_NUM_TO_DISP_ACTSTAT:
            reason_msg = 'Summary statistics disabled for small classes.'
        elif activity.status != 'RLS':
            reason_msg = 'Summary statistics disabled for unreleased activities.'
        activity_stat = None

#    context = {'course': course, 'activity': activity, 'grade': activity.display_grade_student(student.person)}
    context = {'course': course, 'activity': activity, 'grade': grade,
               'activity_stat': activity_stat, 'reason_msg': reason_msg}
    return render_to_response("mobile/activity_info_student.html", context,
                              context_instance=RequestContext(request))
    

def _activity_info_staff(request, course_slug, activity_slug):
    """
    activity detail page
    """
    STUD_NUM_TO_DISP_ACTSTAT = 10
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)
    if len(activities) != 1:
        return NotFoundResponse(request)

    activity = activities[0]

    reason_msg = ''

    if activity.is_numeric():
       activity_stat = generate_numeric_activity_stat(activity)
    else:
       activity_stat = generate_letter_activity_stat(activity)

    context = {'course': course, 'activity': activity, 'activity_stat': activity_stat, 'reason_msg': reason_msg}
    return render_to_response("mobile/activity_info_staff.html", context,
                            context_instance=RequestContext(request))

@requires_course_staff_by_slug
@gzip_page
def student_search(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(offering=course)

    q = request.GET.get('q')
    q = q.encode('ascii','ignore')
    #print q
    try:
        keywords = shlex.split(q)
    except:
        return HttpResponse("Please check your input.")
    if keywords == None :
        context = {'course': course, 'activities': activities}
    else:
        students = Member.objects.filter(role="STUD", offering=course).select_related('person')
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


    context = {'course': course, 'activities': activities, 'student_list':students}
    return render_to_response("mobile/search_student.html", context,
                            context_instance=RequestContext(request))


@requires_course_staff_by_slug
@gzip_page
def class_list(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    
    members = course.member_set.filter(role="STUD").select_related('person')

    context = {'course': course, 'members': members}
    return render_to_response("mobile/class_list.html", context,
                            context_instance=RequestContext(request))


@requires_course_staff_by_slug
@gzip_page
def student_info(request, course_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(offering=course)
    student = Member.objects.get(offering=course, person__userid=userid, role='STUD')

    activities_info = []
    for activity in activities:
        grade = (activity.GradeClass).objects.filter(activity=activity, member=student)
        if not grade:
            # shouldn't display or nothing in database: create temporary nograde object for the template
            grade = (activity.GradeClass)(activity=activity, member=student, flag="NOGR")
        else:
            grade = grade[0]

        submission, submitted_components = get_current_submission(student, activity)
        if submission == None:
            submitted = "No"
        else:
            submitted = "yes"
        activities_info.append({'activity' : activity, 'grade' : grade, 'submitted' : submitted})
    
    context = {'course': course, 'activities_info': activities_info, 'student' : student}
    return render_to_response("mobile/student_info.html", context,
                            context_instance=RequestContext(request))
    
