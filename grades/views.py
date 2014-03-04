import unicodecsv as csv
import pickle
import datetime
import os

from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django.db.models import Q
from django.db.models.aggregates import Max
from django.shortcuts import render, render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.html import mark_safe
from django.conf import settings

from coredata.models import Member, CourseOffering, Person, Semester

from courselib.auth import ForbiddenResponse, NotFoundResponse, is_course_student_by_slug
from courselib.auth import is_course_staff_by_slug, requires_course_staff_by_slug

from grades.models import all_activities_filter
from grades.models import Activity, NumericActivity, LetterActivity, CalNumericActivity, GradeHistory
from grades.models import NumericGrade, LetterGrade
from grades.models import CalLetterActivity, ACTIVITY_TYPES
from grades.models import neaten_activity_positions
from grades.forms import NumericActivityForm, LetterActivityForm, CalNumericActivityForm, MessageForm
from grades.forms import ActivityFormEntry, FormulaFormEntry, StudentSearchForm, FORMTYPE
from grades.forms import GROUP_STATUS_MAP, CourseConfigForm, CalLetterActivityForm, CutoffForm
from grades.formulas import EvalException, activities_dictionary, eval_parse
from grades.utils import reorder_course_activities
from grades.utils import ORDER_TYPE, FormulaTesterActivityEntry, FakeActivity, FakeEvalActivity
from grades.utils import generate_numeric_activity_stat,generate_letter_activity_stat
from grades.utils import ValidationError, calculate_numeric_grade, calculate_letter_grade

from marking.models import get_group_mark, StudentActivityMark, GroupActivityMark, ActivityComponent

from groups.models import GroupMember, add_activity_to_group

from submission.models import SubmissionComponent, GroupSubmission, StudentSubmission, get_current_submission, select_all_submitted_components, select_all_components

from log.models import LogEntry
from pages.models import Page, ACL_ROLES
from dashboard.models import UserConfig, NewsItem
from dashboard.views import _get_memberships
from dashboard.photos import fetch_photos
from discuss import activity as discuss_activity
import celery


FROMPAGE = {'course': 'course', 'activityinfo': 'activityinfo', 'activityinfo_group' : 'activityinfo_group'}

# Course should have this number to student to display the activity statistics, including histogram
STUD_NUM_TO_DISP_ACTSTAT = 10

# Only for display purpose.
ACTIVITY_TYPE = {'NG': 'Numeric Graded', 'LG': 'Letter Graded',
                 'CNG': 'Calculated Numeric Graded', 'CLG': 'Calculated Letter Graded'}

@login_required
def course_info(request, course_slug):
    if is_course_student_by_slug(request, course_slug):
        return _course_info_student(request, course_slug)
    elif is_course_staff_by_slug(request, course_slug):
        return _course_info_staff(request, course_slug)
    else:
        return ForbiddenResponse(request)



@requires_course_staff_by_slug
def reorder_activity(request, course_slug):
    """
    Ajax way to reorder activity.
    This ajax view function is called in the course_info page.
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    if request.method == 'POST':
        neaten_activity_positions(course)
        # find the activities in question
        id_up = request.POST.get('id_up') 
        id_down = request.POST.get('id_down')
        if id_up == None or id_down == None:                      
            return ForbiddenResponse(request)
        # swap the position of the two activities
        activity_up = get_object_or_404(Activity, id=id_up, offering__slug=course_slug)
        activity_down = get_object_or_404(Activity, id=id_down, offering__slug=course_slug)

        temp = activity_up.position
        activity_up.position = activity_down.position
        activity_down.position = temp
        activity_up.save()
        activity_down.save()        
        
        return HttpResponse("Order updated!")
    return ForbiddenResponse(request)

def _course_info_staff(request, course_slug):
    """
    Course front page
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    member = Member.objects.get(offering=course, person__userid=request.user.username, role__in=['INST','TA','APPR'])
    activities = all_activities_filter(offering=course)
    any_group = True in [a.group for a in activities]
    
    # Non Ajax way to reorder activity, please also see reorder_activity view function for ajax way to reorder
    order = None  
    act = None  
    if request.GET.has_key('order'):  
        order = request.GET['order']  
    if request.GET.has_key('act'):  
        act = request.GET['act']  
    if order and act:  
        reorder_course_activities(activities, act, order)  
        return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course_slug}))  


    # Todo: is the activity type necessary?
    activities_info = []
    total_percent = 0
    for activity in activities:
        if activity.percent:
            total_percent += activity.percent

        if isinstance(activity, NumericActivity):
            activities_info.append({'activity':activity, 'type':ACTIVITY_TYPE['NG']})            
        elif isinstance(activity, LetterActivity):
            activities_info.append({'activity':activity, 'type':ACTIVITY_TYPE['LG']})
    
    if len(activities) == 0:
        messages.info(request, "Students won't see this course in their menu on the front page. As soon as some activities have been added, they will see a link to the course info page.")
    
    discussion_activity = False
    if course.discussion:
        discussion_activity = discuss_activity.recent_activity(member)
    
    context = {'course': course, 'member': member, 'activities_info': activities_info, 'from_page': FROMPAGE['course'],
               'order_type': ORDER_TYPE, 'any_group': any_group, 'total_percent': total_percent, 'discussion_activity': discussion_activity}
    return render_to_response("grades/course_info_staff.html", context,
                              context_instance=RequestContext(request))


@requires_course_staff_by_slug
def course_config(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    if request.method=="POST":
        form = CourseConfigForm(request.POST)
        if form.is_valid():
            course.set_url(form.cleaned_data['url'])
            course.set_taemail(form.cleaned_data['taemail'])
            course.set_discussion(form.cleaned_data['discussion'])
            if course.uses_svn():
                course.set_indiv_svn(form.cleaned_data['indiv_svn'])
            course.save()
            messages.success(request, 'Course config updated')

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("updated config for %s") % (course),
                  related_object=course)
            l.save()

            return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course_slug}))
    else:
        form = CourseConfigForm({'url': course.url(), 'taemail': course.taemail(), 'discussion': course.discussion(), 'indiv_svn': course.indiv_svn()})
    
    context = {'course': course, 'form': form}
    return render_to_response("grades/course_config.html", context,
                              context_instance=RequestContext(request))

        
#@requires_course_student_by_slug
def _course_info_student(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(offering=course)
    activities = [a for a in activities if a.status in ['RLS', 'URLS']]
    any_group = True in [a.group for a in activities]
    has_index = bool(Page.objects.filter(offering=course, label="Index", can_read__in=ACL_ROLES['STUD']))
    
    activity_data = []
    student = Member.objects.get(offering=course, person__userid=request.user.username, role='STUD')
    for activity in activities:
        data = {}
        data['act'] = activity
        data['grade_display'] = activity.display_grade_student(student.person)
        activity_data.append(data)
        
    discussion_activity = False
    member = Member.objects.get(offering=course, person__userid=request.user.username, role='STUD')    
    if course.discussion:
        discussion_activity = discuss_activity.recent_activity(member)
        
    context = {'course': course, 'member': student, 'activity_data': activity_data, 'any_group': any_group, 
               'has_index': has_index, 'from_page': FROMPAGE['course'], 'discussion_activity': discussion_activity}
    
    return render_to_response("grades/course_info_student.html", context,
                              context_instance=RequestContext(request))

@login_required
def activity_info_oldurl(request, course_slug, activity_slug, tail):
    """
    Redirect old activity URLs to new (somewhat intelligently: don't redirect if there's no activity there)
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=course)
    act_url = reverse('grades.views.activity_info', kwargs={'course_slug': course.slug, 'activity_slug': activity.slug})
    return HttpResponseRedirect(act_url + tail)

@login_required
def activity_info(request, course_slug, activity_slug):
    if is_course_student_by_slug(request, course_slug):
        return _activity_info_student(request, course_slug, activity_slug)
    elif is_course_staff_by_slug(request, course_slug):
        return _activity_info_staff(request, course_slug, activity_slug)
    else:
        return ForbiddenResponse(request)

def _activity_info_staff(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)
    if len(activities) != 1:
        return NotFoundResponse(request)
    
    activity = activities[0]

    # build list of all students and grades
    students = Member.objects.filter(role="STUD", offering=activity.offering).select_related('person')
    if activity.is_numeric():
        grades_list = activity.numericgrade_set.filter().select_related('member__person', 'activity')
    else:
        grades_list = activity.lettergrade_set.filter().select_related('member__person', 'activity')
    
    grades = {}
    for g in grades_list:
        grades[g.member.person.userid] = g

    source_grades = {}
    if activity.is_calculated() and not activity.is_numeric():
        # calculated letter needs source grades too
        source_list = activity.numeric_activity.numericgrade_set.filter().select_related('member__person', 'activity')
        for g in source_list:
            source_grades[g.member.person.userid] = g

    # collect group membership info
    group_membership = {}
    if activity.group:
        gms = GroupMember.objects.filter(activity=activity, confirmed=True).select_related('group', 'student__person', 'group__courseoffering')
        for gm in gms:
            group_membership[gm.student.person.userid] = gm.group

    # collect submission status
    sub_comps = [sc.title for sc in SubmissionComponent.objects.filter(activity=activity, deleted=False)]
    submitted = {}
    if activity.group:
        subs = GroupSubmission.objects.filter(activity=activity).select_related('group')
        for s in subs:
            members = s.group.groupmember_set.filter(activity=activity)
            for m in members:
                submitted[m.student.person.userid] = True
    else:
        subs = StudentSubmission.objects.filter(activity=activity)
        for s in subs:
            submitted[s.member.person.userid] = True

    if bool(sub_comps) and not bool(activity.due_date):
        messages.warning(request, 'Students will not be able to submit: no due date/time is set.')

    # collect marking status
    mark_comps = [ac.title for ac in ActivityComponent.objects.filter(numeric_activity=activity, deleted=False)]
    marked = {}
    marks = StudentActivityMark.objects.filter(activity=activity).select_related('numeric_grade__member__person')
    for m in marks:
        marked[m.numeric_grade.member.person.userid] = True
    if activity.group:
        # also collect group marks: attribute to both the group and members
        marks = GroupActivityMark.objects.filter(activity=activity).select_related('group')
        for m in marks:
            marked[m.group.slug] = True
            members = m.group.groupmember_set.filter(activity=activity).select_related('student__person')
            for m in members:
                marked[m.student.person.userid] = True
            

    context = {'course': course, 'activity': activity, 'students': students, 'grades': grades, 'source_grades': source_grades,
               'activity_view_type': 'individual', 'group_membership': group_membership,
               'from_page': FROMPAGE['activityinfo'],
               'sub_comps': sub_comps, 'mark_comps': mark_comps,
               'submitted': submitted, 'marked': marked}
    return render_to_response('grades/activity_info.html', context, context_instance=RequestContext(request))


def _activity_info_student(request, course_slug, activity_slug):
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
    
    # only display summary stats for courses with at least STUD_NUM_TO_DISP_ACTSTAT grades received
    reason_msg = ''
    
    if activity.is_numeric():
        activity_stat = generate_numeric_activity_stat(activity)
    else:
        activity_stat = generate_letter_activity_stat(activity)

    if activity_stat is None or activity_stat.count < STUD_NUM_TO_DISP_ACTSTAT:
        reason_msg = 'Summary statistics disabled for small classes.'
        activity_stat = None
    elif activity.status != 'RLS':
        reason_msg = 'Summary statistics disabled for unreleased activities.'
        activity_stat = None

    context = {'course': course, 'activity': activity, 'grade': grade,
               'activity_stat': activity_stat, 'reason_msg': reason_msg}
    return render_to_response('grades/activity_info_student.html', context, context_instance=RequestContext(request))


@requires_course_staff_by_slug
def activity_info_with_groups(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)
    if len(activities) != 1:
        return NotFoundResponse(request)
    
    activity = activities[0]
    if not activity.group:
        return NotFoundResponse(request)

    # build list of group grades information
    all_members = GroupMember.objects.select_related('group', 'student__person', 'group__courseoffering').filter(activity = activity, confirmed = True)
    groups_found = {}
    grouped_students = 0
    for member in all_members:
        grouped_students += 1
        group = member.group
        student = member.student
        if not groups_found.has_key(group.id):
            # a new group discovered by its first member
            # get the current grade of the group 
            current_mark = get_group_mark(activity, group)
            value = 'no grade' if current_mark is None else current_mark.mark
            new_group_grade_info = {'group': group, 'members': [student], 'grade': value}            
            groups_found[group.id] = new_group_grade_info
        else:   
            # add this member to its corresponding group info          
            group_grade_info = groups_found[group.id]
            group_grade_info['members'].append(student)
    
    ungrouped_students = Member.objects.filter(offering = course, role = 'STUD').count() - grouped_students 

    # collect submission status
    submitted = {}
    subs = GroupSubmission.objects.filter(activity=activity).select_related('group')
    for s in subs:
        submitted[s.group.slug] = True
    
    if isinstance(activity, NumericActivity):
        activity_type = ACTIVITY_TYPE['NG']
    elif isinstance(activity, LetterActivity):
        activity_type = ACTIVITY_TYPE['LG']
    
    # more activity info for display
    sub_comps = [sc.title for sc in SubmissionComponent.objects.filter(activity=activity, deleted=False)]
    mark_comps = [ac.title for ac in ActivityComponent.objects.filter(numeric_activity=activity, deleted=False)]

    context = {'course': course, 'activity_type': activity_type, 
               'activity': activity, 'ungrouped_students': ungrouped_students,
               'activity_view_type': 'group',
               'group_grade_info_list': groups_found.values(), 'from_page': FROMPAGE['activityinfo_group'],
               'sub_comps': sub_comps, 'mark_comps': mark_comps,
               'submitted': submitted}
    return render_to_response('grades/activity_info_with_groups.html', context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def activity_stat(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)
    
    if len(activities) != 1:
        return NotFoundResponse(request)

    activity = activities[0]
    display_summary = True # always display for staff
    
    if activity.is_numeric():
        activity_stat = generate_numeric_activity_stat(activity)
        GradeClass = NumericGrade
    else:
        activity_stat = generate_letter_activity_stat(activity)
        GradeClass = LetterGrade
    
    # counts submissions (individual & group)
    submark_stat = {}
    submark_stat['submittable'] = bool(SubmissionComponent.objects.filter(activity=activity))
    submark_stat['studentsubmissons'] = len(set((s.member for s in StudentSubmission.objects.filter(activity=activity))))
    submark_stat['groupsubmissons'] = len(set((s.group for s in GroupSubmission.objects.filter(activity=activity))))
    
    # build counts of how many times each component has been submitted (by unique members/groups)
    sub_comps = select_all_components(activity)
    subed_comps = dict(((comp.id, set()) for comp in sub_comps))
    # build dictionaries of submisson.id -> owner so we can look up quickly when scanning
    subid_dict = dict(((s.id, ("s", s.member_id)) for s in StudentSubmission.objects.filter(activity=activity)))
    subid_dict.update( dict(((s.id, ("g", s.group_id)) for s in GroupSubmission.objects.filter(activity=activity))) )
    
    # build sets of who has submitted each SubmissionComponent
    for sc in select_all_submitted_components(activity=activity):
        if sc.component.deleted:
            # don't report on deleted components
            continue
        owner = subid_dict[sc.submission_id]
        subed_comps[sc.component_id].add(owner)
    
    # actual list of components and counts
    sub_comp_rows = []
    for comp in sub_comps:
        data = {'comp': comp, 'count': len(subed_comps[comp.id])}
        sub_comp_rows.append(data)
    
    submark_stat['studentgrades'] = len(set([s.member for s in GradeClass.objects.filter(activity=activity)]))
    if activity.is_numeric():
        submark_stat['markable'] = bool(ActivityComponent.objects.filter(numeric_activity=activity))
        submark_stat['studentmarks'] = len(set([s.numeric_grade.member for s in StudentActivityMark.objects.filter(activity=activity)]))
        submark_stat['groupmarks'] = len(set([s.group for s in GroupActivityMark.objects.filter(activity=activity)]))
    else:
        submark_stat['markable'] = False


    context = {'course': course, 'activity': activity, 'activity_stat': activity_stat, 'display_summary': display_summary, 'submark_stat': submark_stat, 'sub_comp_rows': sub_comp_rows}
    return render_to_response('grades/activity_stat.html', context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def activity_choice(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    context = {'course': course}
    return render_to_response('grades/activity_choice.html', context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def edit_cutoffs(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(CalLetterActivity, slug=activity_slug, offering=course, deleted=False)    
    if request.method == 'POST':
        form = CutoffForm(request.POST)
        if form.is_valid(): # All validation rules pass
            activity.set_cutoffs(form.cleaned_data['cutoffs'])
            activity.save()
           
            if form.cleaned_data['ap'] > activity.numeric_activity.max_grade:
                messages.warning(request, "Some grade cutoffs are higher than the maximum grade for %s." % (activity.numeric_activity.name))

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
            description=("edited %s cutoffs") % (activity),
            related_object=activity)
            l.save()
            messages.success(request, "Grade cutoffs updated.")

            try:
                ignored = calculate_letter_grade(course, activity)
                if ignored == 1:
                    messages.warning(request, "Did not calculate letter grade for 1 manually-graded student.")
                elif ignored > 1:
                    messages.warning(request, "Did not calculate letter grade for %i manually-graded students." % (ignored))
            except ValidationError as e:
                messages.error(request, e.args[0])
            except NotImplementedError:
                return NotFoundResponse(request)

            return HttpResponseRedirect(reverse('grades.views.activity_info', kwargs={'course_slug': course.slug, 'activity_slug': activity.slug}))
    else:
        cutoff=activity.get_cutoffs()
        cutoffsdict=_cutoffsdict(cutoff)
        form=CutoffForm(cutoffsdict)

    source_grades = activity.numeric_activity.numericgrade_set.exclude(flag="NOGR")
    source_grades = '[' + ", ".join(["%.2f" % (g.value) for g in source_grades]) + ']'

    context = {'course': course, 'activity': activity, 'cutoff':form, 'source_grades': source_grades}
    return render_to_response('grades/edit_cutoffs.html', context, context_instance=RequestContext(request))

def _cutoffsdict(cutoff):
    data = dict()
    data['ap'] = cutoff[0]
    data['a'] = cutoff[1]
    data['am'] = cutoff[2]
    data['bp'] = cutoff[3]
    data['b'] = cutoff[4]
    data['bm'] = cutoff[5]
    data['cp'] = cutoff[6]
    data['c'] = cutoff[7]
    data['cm'] = cutoff[8]
    data['d'] = cutoff[9]
    return data

@requires_course_staff_by_slug
def compare_official(request, course_slug, activity_slug):
    """
    Screen to compare member.official_grade to this letter activity
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(LetterActivity, slug=activity_slug, offering=course, deleted=False)
    
    members = Member.objects.filter(offering=course, role='STUD')
    grades = dict(((g.member, g.letter_grade)for g in LetterGrade.objects.filter(activity=activity).exclude(flag='NOGR')))
    data = []
    
    for m in members:
        if m in grades:
            g = grades[m]
        else:
            g = None
        data.append((m, g, m.official_grade!=g))
    
    #print data
    context = {'course': course, 'activity': activity, 'data': data}
    return render_to_response('grades/compare_official.html', context, context_instance=RequestContext(request))

from dashboard.letters import grade_change_form
@requires_course_staff_by_slug
def grade_change(request, course_slug, activity_slug, userid):
    """
    Produce grade change form
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(LetterActivity, slug=activity_slug, offering=course, deleted=False)
    member = get_object_or_404(Member, person__userid=userid, offering__slug=course_slug)
    user = Person.objects.get(userid=request.user.username)
    grades = LetterGrade.objects.filter(activity=activity, member=member).exclude(flag='NOGR')
    if grades:
        grade = grades[0].letter_grade
    else:
        grade = None
     
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename="%s-gradechange.pdf"' % (userid)
    grade_change_form(member, member.official_grade, grade, user, response)
    return response

    



@requires_course_staff_by_slug
def add_numeric_activity(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)

    activities_list = [(None, u'\u2014'),]
    activities = all_activities_filter(course)
    for a in activities:
        if a.group == True:
            activities_list.append((a.slug, a.name))
    
    if request.method == 'POST': # If the form has been submitted...
        form = NumericActivityForm(request.POST, previous_activities=activities_list) # A form bound to the POST data
        form.activate_addform_validation(course_slug)
        if form.is_valid(): # All validation rules pass
            try:
                aggr_dict = Activity.objects.filter(offering=course).aggregate(Max('position'))
                if not aggr_dict['position__max']:
                    position = 1
                else:
                    position = aggr_dict['position__max'] + 1
                config = {
                        'showstats': form.cleaned_data['showstats'],
                        'showhisto': form.cleaned_data['showhisto'],
                        'url': form.cleaned_data['url'],
                        }
                a = NumericActivity.objects.create(name=form.cleaned_data['name'],
                                                short_name=form.cleaned_data['short_name'],
                                                status=form.cleaned_data['status'],
                                                due_date=form.cleaned_data['due_date'],
                                                percent=form.cleaned_data['percent'],
                                                max_grade=form.cleaned_data['max_grade'],
                                                offering=course, position=position,
                                                group=GROUP_STATUS_MAP[form.cleaned_data['group']],
                                                config=config)
                if a.group == True and form.cleaned_data['extend_group'] is not None:
                    a2 = [i for i in activities if i.slug == form.cleaned_data['extend_group']]
                    if len(a2) > 0:
                        add_activity_to_group(a, a2[0], course)
                
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("created a numeric activity %s") % (a),
                      related_object=a)
                l.save()
            except NotImplementedError:
                return NotFoundResponse(request)
            
            messages.success(request, 'New activity "%s" added' % a.name)
            _semester_date_warning(request, a)
            
            return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course_slug}))
        else:
            messages.error(request, "Please correct the error below")
    else:
        form = NumericActivityForm(previous_activities=activities_list)
    context = {'course': course, 'form': form, 'form_type': FORMTYPE['add']}
    return render_to_response('grades/numeric_activity_form.html', context, context_instance=RequestContext(request))
    
@requires_course_staff_by_slug
def add_cal_numeric_activity(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    numeric_activities = NumericActivity.objects.filter(offering=course, deleted=False)
    
    if request.method == 'POST': # If the form has been submitted...
        form = CalNumericActivityForm(request.POST) # A form bound to the POST data
        form.activate_addform_validation(course_slug)
        if form.is_valid(): # All validation rules pass
            try:
                aggr_dict = Activity.objects.filter(offering=course).aggregate(Max('position'))
                if not aggr_dict['position__max']:
                    position = 1
                else:
                    position = aggr_dict['position__max'] + 1
                config = {
                        'showstats': form.cleaned_data['showstats'],
                        'showhisto': form.cleaned_data['showhisto'],
                        'url': form.cleaned_data['url'],
                        }
                CalNumericActivity.objects.create(name=form.cleaned_data['name'],
                                                short_name=form.cleaned_data['short_name'],
                                                status=form.cleaned_data['status'],
                                                percent=form.cleaned_data['percent'],
                                                max_grade=form.cleaned_data['max_grade'],
                                                formula=form.cleaned_data['formula'],
                                                offering=course, 
                                                position=position,
                                                group=False,
                                                config=config)
            except NotImplementedError:
                return NotFoundResponse(request)
            
            messages.success(request, 'New activity "%s" added' % form.cleaned_data['name'])
            return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course_slug}))
        else:
            messages.error(request, "Please correct the error below")
    else:
        form = CalNumericActivityForm(initial={'formula': '[[activitytotal]]'})
    context = {'course': course, 'form': form, 'numeric_activities': numeric_activities, 'form_type': FORMTYPE['add']}
    return render_to_response('grades/cal_numeric_activity_form.html', context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def add_cal_letter_activity(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    letter_activities = LetterActivity.objects.filter(offering=course)
    numact_choices = [(na.pk, na.name) for na in NumericActivity.objects.filter(offering=course, deleted=False)]
    examact_choices = [(0, u'\u2014')] + [(na.pk, na.name) for na in Activity.objects.filter(offering=course, deleted=False)]

    if request.method == 'POST': # If the form has been submitted...
        form = CalLetterActivityForm(request.POST) # A form bound to the POST data
        form.fields['numeric_activity'].choices = numact_choices
        form.fields['exam_activity'].choices = examact_choices
        form.activate_addform_validation(course_slug)
        if form.is_valid(): # All validation rules pass
            try:
                aggr_dict = Activity.objects.filter(offering=course).aggregate(Max('position'))
                if not aggr_dict['position__max']:
                    position = 1
                else:
                    position = aggr_dict['position__max'] + 1

                if form.cleaned_data['exam_activity'] == '0':
                    exam_activity = None
                else:
                    exam_activity = Activity.objects.get(pk=form.cleaned_data['exam_activity'])

                config = {
                        'showstats': form.cleaned_data['showstats'],
                        'showhisto': form.cleaned_data['showhisto'],
                        'url': form.cleaned_data['url'],
                        }
                CalLetterActivity.objects.create(name=form.cleaned_data['name'],
                                                short_name=form.cleaned_data['short_name'],
                                                status=form.cleaned_data['status'],
                                                numeric_activity=NumericActivity.objects.get(pk=form.cleaned_data['numeric_activity']),
                                                exam_activity=exam_activity,
                                                offering=course, 
                                                position=position,
                                                group=False,
                                                config=config)
            except NotImplementedError:
                return NotFoundResponse(request)
            
            messages.success(request, 'New activity "%s" added' % form.cleaned_data['name'])
            return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course_slug}))
        else:
            messages.error(request, "Please correct the error below")
    else:
        form = CalLetterActivityForm()
        form.fields['numeric_activity'].choices = numact_choices
        form.fields['exam_activity'].choices = examact_choices
    context = {'course': course, 'form': form, 'letter_activities': letter_activities, 'form_type': FORMTYPE['add']}
    return render_to_response('grades/cal_letter_activity_form.html', context, context_instance=RequestContext(request))


@requires_course_staff_by_slug
def formula_tester(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    numeric_activities = NumericActivity.objects.filter(offering=course, deleted=False)
    result = ""
    
    if 'formula' in request.GET: # If the form has been submitted...
        activity_entries = []
        faked_activities = [] # used to evaluate the formula
        has_error = False
        for numeric_activity in numeric_activities:
            activity_form_entry = ActivityFormEntry(request.GET, prefix=numeric_activity.slug)
            if not activity_form_entry.is_valid():
                has_error = True
            else:
                value = activity_form_entry.cleaned_data['value']
                if not value:
                    value = 0
                faked_activities.append(FakeActivity(numeric_activity.name, numeric_activity.short_name,
                                                     activity_form_entry.cleaned_data['status'],
                                                     numeric_activity.max_grade, numeric_activity.percent,
                                                     value))
            activity_entries.append(FormulaTesterActivityEntry(numeric_activity, activity_form_entry))
            

        formula_form_entry = FormulaFormEntry(request.GET)
        formula_form_entry.activate_form_entry_validation(course_slug, None)
        
        if not formula_form_entry.is_valid():
            has_error = True
        if has_error:
            messages.error(request, "Please correct the error below")
        else:
            parsed_expr = pickle.loads(formula_form_entry.pickled_formula)
            act_dict = activities_dictionary(faked_activities)
            try:
                result = eval_parse(parsed_expr, FakeEvalActivity(course), act_dict, None, True)
            except EvalException:
                messages.error(request,  "Can not evaluate formula")
    else:
        activity_entries = []
        for numeric_activity in numeric_activities:
            activity_form_entry = ActivityFormEntry(prefix=numeric_activity.slug)
            activity_entries.append(FormulaTesterActivityEntry(numeric_activity, activity_form_entry))
        formula_form_entry = FormulaFormEntry()
    context = {'course': course, 'activity_entries': activity_entries,
               'formula_form_entry': formula_form_entry, 'result': result}
    return render_to_response('grades/formula_tester.html', context, context_instance=RequestContext(request))
    
@requires_course_staff_by_slug
def calculate_all(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(CalNumericActivity, slug=activity_slug, offering=course, deleted=False)
    
    try:
        ignored = calculate_numeric_grade(course,activity)
        if ignored==1:
            messages.warning(request, "Did not calculate grade for 1 manually-graded student.")
        elif ignored>1:
            messages.warning(request, "Did not calculate grade for %i manually-graded students." % (ignored))
    except ValidationError as e:
        messages.error(request, e.args[0])
    except EvalException as e:
        messages.error(request, e.args[0])
    except NotImplementedError:
        return NotFoundResponse(request)

    return HttpResponseRedirect(activity.get_absolute_url())


@requires_course_staff_by_slug
def calculate_all_lettergrades(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(CalLetterActivity, slug=activity_slug, offering=course, deleted=False)
    
    try:
        ignored = calculate_letter_grade(course,activity)
        if ignored==1:
            messages.warning(request, "Did not calculate letter grade for 1 manually-graded student.")
        elif ignored>1:
            messages.warning(request, "Did not calculate letter grade for %i manually-graded students." % (ignored))
    except ValidationError as e:
        messages.error(request, e.args[0])
    except NotImplementedError:
        return NotFoundResponse(request)

    return HttpResponseRedirect(activity.get_absolute_url())



@requires_course_staff_by_slug
def calculate_individual_ajax(request, course_slug, activity_slug):
    """
    Ajax way to calculate individual numeric grade.
    This ajav view function is called in the activity_info page.
    """
    if request.method == 'POST':
        userid = request.POST.get('userid') 
        if userid == None:                      
            return ForbiddenResponse(request)
            
        course = get_object_or_404(CourseOffering, slug=course_slug)
        activity = get_object_or_404(CalNumericActivity, slug=activity_slug, offering=course, deleted=False)
        member = get_object_or_404(Member, offering=course, person__userid=userid, role='STUD')

        try:
            displayable_result = calculate_numeric_grade(course,activity, member)
        except ValidationError:
            return ForbiddenResponse(request)
        except EvalException:
            return ForbiddenResponse(request)
        except NotImplementedError:
            return ForbiddenResponse(request)
        return HttpResponse(displayable_result)
    return ForbiddenResponse(request)

def _create_activity_formdatadict(activity):
    if not [activity for activity_type in ACTIVITY_TYPES if isinstance(activity, activity_type)]:
        return
    data = dict()
    data['name'] = activity.name
    data['short_name'] = activity.short_name
    data['status'] = activity.status
    data['due_date'] = activity.due_date
    data['percent'] = activity.percent
    data['url'] = ''
    if 'url' in activity.config:
        data['url'] = activity.config['url']
    data['showstats'] = True
    if 'showstats' in activity.config:
        data['showstats'] = activity.config['showstats']
    data['showhisto'] = True
    if 'showhisto' in activity.config:
        data['showhisto'] = activity.config['showhisto']

    for (k, v) in GROUP_STATUS_MAP.items():
        if activity.group == v:
            data['group'] = k
    if isinstance(activity, NumericActivity):
        data['max_grade'] = activity.max_grade
    if isinstance(activity, CalNumericActivity):
        data['formula'] = activity.formula
    if isinstance(activity, CalLetterActivity):
        data['numeric_activity'] = activity.numeric_activity_id
        data['exam_activity'] = activity.exam_activity_id
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
    if data.has_key('group'):
        activity.group = GROUP_STATUS_MAP[data['group']]
    if data.has_key('max_grade'):
        activity.max_grade = data['max_grade']
    if data.has_key('formula'):
        activity.formula = data['formula']
    if data.has_key('url'):
        activity.config['url'] = data['url']
    if data.has_key('showstats'):
        activity.config['showstats'] = data['showstats']
    if data.has_key('showhisto'):
        activity.config['showhisto'] = data['showhisto']
    if data.has_key('numeric_activity'):
        activity.numeric_activity = NumericActivity.objects.get(pk=data['numeric_activity'])
    if data.has_key('exam_activity'):
        try:
            activity.exam_activity = Activity.objects.get(pk=data['exam_activity'])
        except Activity.DoesNotExist:
            activity.exam_activity = None

def _semester_date_warning(request, activity):
    """
    Generate warnings for this request if activity due date is outside semester boundaries.
    """
    if not activity.due_date:
        return

    # don't warn for 24 hours after the last day of classes (start of last day + 48 hours)
    if activity.due_date > datetime.datetime.combine(
            activity.offering.semester.end, datetime.time(0,0,0)) + datetime.timedelta(hours=48):
        messages.warning(request, "Activity is due after the end of the semester.")
    if activity.due_date < datetime.datetime.combine(
            activity.offering.semester.start, datetime.time(0,0,0)):
        messages.warning(request, "Activity is due before the start of the semester.")


@requires_course_staff_by_slug
def edit_activity(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(slug=activity_slug, offering=course)

    numact_choices = [(na.pk, na.name) for na in NumericActivity.objects.filter(offering=course, deleted=False)]
    examact_choices = [(0, u'\u2014')] + [(na.pk, na.name) for na in Activity.objects.filter(offering=course, deleted=False)]
    if (len(activities) == 1):
        activity = activities[0]

        # extend group options
        activities_list = [(None, u'\u2014'),]
        activities = all_activities_filter(offering=course)
        for a in activities:
            if a.group == True and a.id != activity.id:
                activities_list.append((a.slug, a.name))

        from_page = request.GET.get('from_page')
        
        if request.method == 'POST': # If the form has been submitted...
            if isinstance(activity, CalNumericActivity):
                form = CalNumericActivityForm(request.POST)
            elif isinstance(activity, NumericActivity):
                form = NumericActivityForm(request.POST, previous_activities=activities_list) 
            elif isinstance(activity, CalLetterActivity):
                form = CalLetterActivityForm(request.POST)
                form.fields['numeric_activity'].choices = numact_choices
                form.fields['exam_activity'].choices = examact_choices
            elif isinstance(activity, LetterActivity):
                form = LetterActivityForm(request.POST, previous_activities=activities_list)

            form.activate_editform_validation(course_slug, activity_slug)
            
            if  form.is_valid(): # All validation rules pass                	
                _populate_activity_from_formdata(activity, form.cleaned_data)

                if activity.group == True and form.cleaned_data['extend_group'] is not None:
                    a2 = [i for i in activities if i.slug == form.cleaned_data['extend_group']]
                    if len(a2) > 0:
                        add_activity_to_group(activity, a2[0], course)
                
                activity.save(entered_by=request.user.username)
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("edited %s") % (activity),
                      related_object=activity)
                l.save()
                messages.success(request, "Details of %s updated" % activity.name)
                _semester_date_warning(request, activity)

                if from_page == FROMPAGE['course']:
                    return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course_slug}))
                else:
                    return HttpResponseRedirect(reverse('grades.views.activity_info',
                                                        kwargs={'course_slug': course_slug, 'activity_slug': activity.slug}))
            else:
                messages.error(request, "Please correct the error below")
        else:
            datadict = _create_activity_formdatadict(activity)
            if isinstance(activity, CalNumericActivity):
                form = CalNumericActivityForm(datadict)
            elif isinstance(activity, NumericActivity):
                form = NumericActivityForm(datadict, previous_activities=activities_list)
            elif isinstance(activity, CalLetterActivity):
                form = CalLetterActivityForm(datadict)
                form.fields['numeric_activity'].choices = numact_choices
                form.fields['exam_activity'].choices = examact_choices
                # set initial value in form to current value
            elif isinstance(activity, LetterActivity):
                form = LetterActivityForm(datadict, previous_activities=activities_list)
            elif isinstance(activity, CalLetterActivity):
                form = CalLetterActivityForm(datadict)
                form.fields['numeric_activity'].choices = numact_choices
                form.fields['exam_activity'].choices = examact_choices

            form.activate_editform_validation(course_slug, activity_slug)
        
        if isinstance(activity, CalNumericActivity):
            numeric_activities = NumericActivity.objects.exclude(slug=activity_slug).filter(offering=course, deleted=False)
            context = {'course': course, 'activity': activity, 'form': form, 'numeric_activities': numeric_activities, 'form_type': FORMTYPE['edit'], 'from_page': from_page}
            return render_to_response('grades/cal_numeric_activity_form.html', context, context_instance=RequestContext(request))
        elif isinstance(activity, NumericActivity):
            context = {'course': course, 'activity': activity, 'form': form, 'form_type': FORMTYPE['edit'], 'from_page': from_page}
            return render_to_response('grades/numeric_activity_form.html', context, context_instance=RequestContext(request))
        elif isinstance(activity, CalLetterActivity):
            context = {'course': course, 'activity': activity, 'form': form, 'form_type': FORMTYPE['edit'], 'from_page': from_page}
            return render_to_response('grades/cal_letter_activity_form.html', context, context_instance=RequestContext(request))
        elif isinstance(activity, LetterActivity):
            context = {'course': course, 'activity': activity, 'form': form, 'form_type': FORMTYPE['edit'], 'from_page': from_page}
            return render_to_response('grades/letter_activity_form.html', context, context_instance=RequestContext(request))       
    else:
        return NotFoundResponse(request)
    

@requires_course_staff_by_slug
def delete_activity(request, course_slug, activity_slug):
    """
    Flag activity as deleted
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=course)

    if request.method == 'POST':
        if not Member.objects.filter(offering=course, person__userid=request.user.username, role="INST"):
            # only instructors can delete
            return ForbiddenResponse(request, "Only instructors can delete activities")
    
        activity.safely_delete()
        messages.success(request, 'Activity deleted.  It can be restored by the system adminstrator in an emergency.')

        #LOG EVENT#
        l = LogEntry(userid=request.user.username,
              description=("activity %s marked deleted") % (activity),
              related_object=course)
        l.save()

        return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course.slug}))

    else:
        return ForbiddenResponse(request)


@requires_course_staff_by_slug
def release_activity(request, course_slug, activity_slug):
    """
    Bump activity status: INVI -> URLS, URLS -> RLS.
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(Activity, slug=activity_slug, offering=course, deleted=False)
    if request.method == 'POST':
        if activity.status == "INVI":
            activity.status = "URLS"
            activity.save(entered_by=request.user.username)
            messages.success(request, 'Activity made visible to students (but grades are still unreleased).')

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("activity %s made visible") % (activity),
                  related_object=course)
            l.save()
        elif activity.status == "URLS":
            activity.status = "RLS"
            activity.save(entered_by=request.user.username)
            messages.success(request, 'Grades released to students.')

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("activity %s grades released") % (activity),
                  related_object=course)
            l.save()

        return HttpResponseRedirect(reverse('grades.views.activity_info', kwargs={'course_slug': course.slug, 'activity_slug': activity.slug}))
            
    else:
        return ForbiddenResponse(request)

    
@requires_course_staff_by_slug
def add_letter_activity(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    
    activities_list = [(None, u'\u2014'),]
    activities = all_activities_filter(course)
    for a in activities:
        if a.group == True:
            activities_list.append((a.slug, a.name))

    if request.method == 'POST': # If the form has been submitted...
        form = LetterActivityForm(request.POST, previous_activities=activities_list) # A form bound to the POST data
        form.activate_addform_validation(course_slug)
        if form.is_valid(): # All validation rules pass
            #try:
                aggr_dict = Activity.objects.filter(offering=course).aggregate(Max('position'))
                if not aggr_dict['position__max']:
                    position = 1
                else:
                    position = aggr_dict['position__max'] + 1
                config = {
                        'showstats': form.cleaned_data['showstats'],
                        'showhisto': form.cleaned_data['showhisto'],
                        'url': form.cleaned_data['url'],
                        }
                a = LetterActivity.objects.create(name=form.cleaned_data['name'],
                                                short_name=form.cleaned_data['short_name'],
                                                status=form.cleaned_data['status'],
                                                due_date=form.cleaned_data['due_date'],
                                                percent=form.cleaned_data['percent'],
                                                offering=course, position=position,
                                                group=GROUP_STATUS_MAP[form.cleaned_data['group']],
                                                config=config)
                if a.group == True and form.cleaned_data['extend_group'] is not None:
                    a2 = [i for i in activities if i.slug == form.cleaned_data['extend_group']]
                    if len(a2) > 0:
                        add_activity_to_group(a, a2[0], course)

                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                      description=("created a letter-graded activity %s") % (a),
                      related_object=a)
                l.save()
                messages.success(request, 'New activity "%s" added' % a.name)
                _semester_date_warning(request, a)
                
                return HttpResponseRedirect(reverse('grades.views.course_info',
                                                kwargs={'course_slug': course_slug}))
    else:
        form = LetterActivityForm(previous_activities=activities_list)
    activities = course.activity_set.all()
    context = {'course': course, 'form': form, 'form_type': FORMTYPE['add']}
    return render_to_response('grades/letter_activity_form.html', context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def all_grades(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(offering=course)
    students = Member.objects.filter(offering=course, role="STUD").select_related('person', 'offering')
    
    # get grade data into a format we can work with
    grades = {}
    for a in activities:
        grades[a.slug] = {}
        if hasattr(a, 'numericgrade_set'):
            gs = a.numericgrade_set.all().select_related('member', 'member__person')
        else:
            gs = a.lettergrade_set.all().select_related('member', 'member__person')
        for g in gs:
            grades[a.slug][g.member.person.userid] = g

    memberships, excluded=_get_memberships(userid=request.user.username)
    
    context = {'course': course, 'students': students, 'activities': activities, 'grades': grades, 'memberships': memberships}
    return render_to_response('grades/all_grades.html', context, context_instance=RequestContext(request))


def _all_grades_output(response, course):
    activities = all_activities_filter(offering=course)
    students = Member.objects.filter(offering=course, role="STUD").select_related('person')

    # get grade data into a format we can work with
    grades = {}
    for a in activities:
        grades[a.slug] = {}
        if hasattr(a, 'numericgrade_set'):
            gs = a.numericgrade_set.all()
        else:
            gs = a.lettergrade_set.all()
        for g in gs:
            grades[a.slug][g.member.person.userid] = g
    
    # output results
    writer = csv.writer(response)
    row = ['Last name', 'First name', Person.userid_header(), Person.emplid_header()]
    for a in activities:
        row.append(a.short_name)
    writer.writerow(row)
    
    for s in students:
        row = [s.person.last_name, s.person.first_name, s.person.userid, s.person.emplid]
        for a in activities:
            try:
                gr = grades[a.slug][s.person.userid]
                if gr.flag=='NOGR':
                    g = ''
                else:
                    if a.is_numeric():
                        g = gr.value
                    else:
                        g = gr.letter_grade
            except KeyError:
                g = ''
            row.append(g)
        writer.writerow(row)

@requires_course_staff_by_slug
def all_grades_csv(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % (course_slug)
    
    _all_grades_output(response, course)        
    return response

@requires_course_staff_by_slug
def class_list(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    members = Member.objects.filter(offering=course, role="STUD").select_related('person', 'offering')
    
    gms = GroupMember.objects.filter(confirmed=True, student__offering=course).select_related('group', 'group__courseoffering')
    groups = {}
    for gm in gms:
        gs = groups.get(gm.student_id, set())
        groups[gm.student_id] = gs
        gs.add(gm.group)
    
    rows = []
    for m in members:
        data = {'member': m, 'groups': groups.get(m.id, [])}
        rows.append(data)

    memberships, excluded=_get_memberships(userid=request.user.username)
    
    context = {'course': course, 'rows': rows, 'memberships': memberships}
    return render_to_response('grades/class_list.html', context, context_instance=RequestContext(request))


@requires_course_staff_by_slug
def photo_list(request, course_slug):
    user = get_object_or_404(Person, userid=request.user.username)
    configs = UserConfig.objects.filter(user=user, key='photo-agreement')
    
    if not (configs and configs[0].value['agree']):
        url = reverse('dashboard.views.photo_agreement')
        return ForbiddenResponse(request, mark_safe('You must <a href="%s">confirm the photo usage agreement</a> before seeing student photos.' % (url)))
    
    course = get_object_or_404(CourseOffering, slug=course_slug)
    members = Member.objects.filter(offering=course, role="STUD").select_related('person', 'offering')
    
    # fire off a task to fetch the photos, to warm the cache
    task_map = fetch_photos([m.person.emplid for m in members])
    for emplid, task_id in task_map.iteritems():
        cache.set('photo-task-'+unicode(emplid), task_id, 60)

    context = {'course': course, 'members': members}
    return render_to_response('grades/photo_list.html', context, context_instance=RequestContext(request))


@login_required
def student_photo(request, emplid):
    # confirm user's photo agreement
    user = get_object_or_404(Person, userid=request.user.username)
    configs = UserConfig.objects.filter(user=user, key='photo-agreement')
    if not (configs and configs[0].value['agree']):
        url = reverse('dashboard.views.photo_agreement')
        return ForbiddenResponse(request, mark_safe('You must <a href="%s">confirm the photo usage agreement</a> before seeing student photos.' % (url)))

    # confirm user is an instructor of this student (within the last two years)
    # TODO: cache past_semester to save the query?
    past_semester = Semester.get_semester(datetime.date.today() - datetime.timedelta(days=730))
    student_members = Member.objects.filter(offering__semester__name__gte=past_semester.name,
            person__emplid=emplid, role='STUD').select_related('offering')
    student_offerings = [m.offering for m in student_members]
    instructor_of = Member.objects.filter(person=user, role='INST', offering__in=student_offerings)
    if instructor_of.count() == 0:
        return ForbiddenResponse(request, 'You must be an instructor of this student.')

    # get the photo
    from dashboard.tasks import fetch_photos_task
    from dashboard.photos import DUMMY_IMAGE_FILE, PHOTO_TIMEOUT
    task_id = cache.get('photo-task-'+unicode(emplid), None)
    photo_data = cache.get('photo-image-'+unicode(emplid), None)
    data = None
    status = 200

    if photo_data:
        # found image in cache: was fetched previously or task already completed before we got here
        #print "cache data", emplid
        data = photo_data
    elif task_id and settings.USE_CELERY:
        # found a task fetching the photo: wait for it to complete and get the data
        task = fetch_photos_task.AsyncResult(task_id)
        try:
            #print "cache task", emplid
            task.get(timeout=PHOTO_TIMEOUT)
            data = cache.get('photo-image-'+unicode(emplid), None)
        except celery.exceptions.TimeoutError:
            pass
    elif settings.USE_CELERY:
        # no cache warming: new task to get the photo
        #print "no cache", emplid
        task = fetch_photos_task.apply([emplid])
        try:
            data = task.get(timeout=PHOTO_TIMEOUT)
        except celery.exceptions.TimeoutError:
            pass

    if not data:
        # whatever happened above failed: use a no-photo placeholder
        data = open(DUMMY_IMAGE_FILE, 'r').read()
        status = 404

    # return the photo
    response = HttpResponse(data, content_type='image/jpeg')
    response.status_code = status
    response['Content-Disposition'] = 'inline; filename="%s.png"' % (emplid)
    # TODO: be a little less heavy-handed with the caching if it can be done safely
    response['Cache-Control'] = 'no-store'
    response['Pragma'] = 'no-cache'
    return response





@requires_course_staff_by_slug
def new_message(request, course_slug):
    offering = get_object_or_404(CourseOffering, slug=course_slug)
    staff = get_object_or_404(Person, userid=request.user.username)
    default_message = NewsItem(user=staff, author=staff, course=offering, source_app="dashboard")
    if request.method =='POST':
        form = MessageForm(request.POST, instance=default_message)
        if form.is_valid()==True:
            NewsItem.for_members(member_kwargs={'offering': offering}, newsitem_kwargs={
                    'author': staff, 'course': offering, 'source_app': 'dashboard',
                    'title': form.cleaned_data['title'], 'content': form.cleaned_data['content'],
                    'url': form.cleaned_data['url']})

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("created a message for every student in %s") % (offering),
                  related_object=offering)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'News item created.')
            return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': offering.slug}))
    else:
        form = MessageForm()    
    return render(request, "grades/new_message.html", {"form" : form,'course': offering})


@requires_course_staff_by_slug
def student_search(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    if request.method == 'POST':
        # find the student if we can and redirect to info page
        form = StudentSearchForm(request.POST)
        if not form.is_valid():
            messages.add_message(request, messages.ERROR, 'Invalid search')
            context = {'course': course, 'form': form}
            return render_to_response('grades/student_search.html', context, context_instance=RequestContext(request))

        search = form.cleaned_data['search']
        try:
            int(search)
            students = Member.objects.filter(offering=course, role="STUD").filter(Q(person__userid=search) | Q(person__emplid=search))
        except ValueError:
            students = Member.objects.filter(offering=course, role="STUD").filter(person__userid=search)
        
        if len(students)!=1:
            if len(students)==0:
                messages.add_message(request, messages.ERROR, 'No student found')
            else:
                messages.add_message(request, messages.ERROR, 'Multiple students found')
            context = {'course': course, 'form': form}
            return render_to_response('grades/student_search.html', context, context_instance=RequestContext(request))

        student = students[0]
        return HttpResponseRedirect(reverse('grades.views.student_info',
                                                kwargs={'course_slug': course_slug, 'userid': student.person.userid}))


    form = StudentSearchForm()
    context = {'course': course, 'form': form}
    return render_to_response('grades/student_search.html', context, context_instance=RequestContext(request))
    

@requires_course_staff_by_slug
def student_info(request, course_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    member = get_object_or_404(Member, person__userid=userid, offering__slug=course_slug)
    activities = all_activities_filter(offering=course)
    
    if member.role != "STUD":
        return NotFoundResponse(request)
    
    grade_info = []
    for a in activities:
        info = {'act': a}
        # get grade
        if hasattr(a, 'numericgrade_set'):
            gs = a.numericgrade_set.filter(member=member)
        else:
            gs = a.lettergrade_set.filter(member=member)

        if gs:
            info['grade'] = gs[0]
        else:
            info['grade'] = None

        # find most recent submission
        sub, _ = get_current_submission(member.person, a)
        info['sub'] = sub

        grade_info.append(info)
        
        # find marking info
        info['marked'] = False
        if StudentActivityMark.objects.filter(activity=a, numeric_grade__member=member):
            info['marked'] = True
        gms = GroupMember.objects.filter(activity=a, student=member, confirmed=True)
        if gms:
            # in a group
            gm = gms[0]
            if GroupActivityMark.objects.filter(activity=a, group=gm.group):
                info['marked'] = True

    group_memberships = GroupMember.objects.filter(student__person__userid=userid, activity__offering__slug=course_slug)
    grade_history = GradeHistory.objects.filter(member=member, status_change=False).select_related('entered_by', 'activity', 'group', 'mark')
    #grade_history = GradeHistory.objects.filter(member=member).select_related('entered_by', 'activity', 'group', 'mark')

    context = {'course': course, 'member': member, 'grade_info': grade_info, 'group_memberships': group_memberships,
               'grade_history': grade_history}
    return render_to_response('grades/student_info.html', context, context_instance=RequestContext(request))


@requires_course_staff_by_slug
def export_all(request, course_slug):
    """
    Export everything we can about this offering
    """
    import StringIO, tempfile, zipfile, os, json
    from django.http import StreamingHttpResponse
    from django.core.servers.basehttp import FileWrapper
    from marking.views import _mark_export_data, _DecimalEncoder
    from submission.models import generate_submission_contents
    from discuss.models import DiscussionTopic

    course = get_object_or_404(CourseOffering, slug=course_slug)

    handle, filename = tempfile.mkstemp('.zip')
    os.close(handle)
    z = zipfile.ZipFile(filename, 'w')

    # add all grades CSV
    allgrades = StringIO.StringIO()
    _all_grades_output(allgrades, course)    
    z.writestr("grades.csv", allgrades.getvalue())
    allgrades.close()
    
    # add marking data
    acts = all_activities_filter(course)
    for a in acts:
        if ActivityComponent.objects.filter(numeric_activity=a):
            markingdata = _mark_export_data(a)
            markout = StringIO.StringIO()
            json.dump({'marks': markingdata}, markout, cls=_DecimalEncoder, indent=1)
            z.writestr(a.slug + "-marking.json", markout.getvalue())
            del markout, markingdata
    
    # add submissions
    acts = all_activities_filter(course)
    for a in acts:
        if SubmissionComponent.objects.filter(activity=a):
            generate_submission_contents(a, z, prefix=a.slug+'-submissions' + os.sep)

    # add discussion
    if course.discussion():
        topics = DiscussionTopic.objects.filter(offering=course).order_by('-pinned', '-last_activity_at')
        discussion_data = [t.exportable() for t in topics]
        discussout = StringIO.StringIO()
        json.dump(discussion_data, discussout, indent=1)
        z.writestr("discussion.json", discussout.getvalue())
        del discussion_data, discussout

    # return the zip file
    z.close()
    zipdata = open(filename, 'rb')
    response = StreamingHttpResponse(FileWrapper(zipdata), content_type='application/zip')
    response['Content-Length'] = os.path.getsize(filename)    
    response['Content-Disposition'] = 'attachment; filename="' + course.slug + '.zip"'
    try:
        os.remove(filename)
    except OSError:
        pass
    return response

