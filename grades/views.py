from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404, HttpResponseForbidden, HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Q
from django.db.models.aggregates import Max
from coredata.models import Member, CourseOffering, Person, Role
from courselib.auth import *
from grades.models import ACTIVITY_STATUS, all_activities_filter, Activity, \
                        NumericActivity, LetterActivity, CalNumericActivity, CalLetterActivity,ACTIVITY_TYPES
from grades.forms import NumericActivityForm, LetterActivityForm, CalNumericActivityForm, \
                         ActivityFormEntry, FormulaFormEntry, StudentSearchForm, FORMTYPE, GROUP_STATUS_MAP, CourseConfigForm, CalLetterActivityForm, Activity_ChoiceForm, \
                         CutoffForm
from grades.models import *
from grades.utils import StudentActivityInfo, reorder_course_activities, create_StudentActivityInfo_list, \
                        ORDER_TYPE, FormulaTesterActivityEntry, FakeActivity, FakeEvalActivity, \
                        generate_numeric_activity_stat,generate_letter_activity_stat
from grades.utils import ValidationError, parse_and_validate_formula, calculate_numeric_grade,calculate_letter_grade
from marking.models import get_group_mark, StudentActivityMark, GroupActivityMark, ActivityComponent
from groups.models import *
from submission.models import SubmissionComponent, Submission, GroupSubmission, StudentSubmission, get_current_submission, select_all_submitted_components, select_all_components
from log.models import LogEntry
from django.contrib import messages
import pickle, datetime, csv
from grades.formulas import EvalException, activities_dictionary, eval_parse

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
    
    context = {'course': course, 'activities_info': activities_info, 'from_page': FROMPAGE['course'],
               'order_type': ORDER_TYPE, 'any_group': any_group, 'total_percent': total_percent}
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
            course.save()
            messages.success(request, 'Course config updated')

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("updated config for %s") % (course),
                  related_object=course)
            l.save()

            return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course_slug}))
    else:
        form = CourseConfigForm({'url': course.url(), 'taemail': course.taemail()})
    
    context = {'course': course, 'form': form}
    return render_to_response("grades/course_config.html", context,
                              context_instance=RequestContext(request))

        

#@requires_course_student_by_slug
def _course_info_student(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activities = all_activities_filter(offering=course)
    activities = [a for a in activities if a.status in ['RLS', 'URLS']]
    any_group = True in [a.group for a in activities]
    
    activity_data = []
    student = Member.objects.get(offering=course, person__userid=request.user.username, role='STUD')
    for activity in activities:
        data = {}
        data['act'] = activity
        data['grade_display'] = activity.display_grade_student(student.person)
        activity_data.append(data)
    context = {'course': course, 'activity_data': activity_data, 'any_group': any_group, 'from_page': FROMPAGE['course']}
    
    return render_to_response("grades/course_info_student.html", context,
                              context_instance=RequestContext(request))

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
    elif 'showstats' in activity.config and not activity.config['showstats']:
        reason_msg = 'Summary statistics disabled for this activity by instructor.'
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
               ignored = calculate_letter_grade(course,activity)
               if ignored==1:
                  messages.warning(request, "Did not calculate letter grade for 1 manually-graded student.")
               elif ignored>1:
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
                a = NumericActivity.objects.create(name=form.cleaned_data['name'],
                                                short_name=form.cleaned_data['short_name'],
                                                status=form.cleaned_data['status'],
                                                due_date=form.cleaned_data['due_date'],
                                                percent=form.cleaned_data['percent'],
                                                max_grade=form.cleaned_data['max_grade'],
                                                url=form.cleaned_data['url'],
                                                offering=course, position=position,
                                                group=GROUP_STATUS_MAP[form.cleaned_data['group']])
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
                CalNumericActivity.objects.create(name=form.cleaned_data['name'],
                                                short_name=form.cleaned_data['short_name'],
                                                status=form.cleaned_data['status'],
                                                url=form.cleaned_data['url'],
                                                percent=form.cleaned_data['percent'],
                                                max_grade=form.cleaned_data['max_grade'],
                                                formula=form.cleaned_data['formula'],
                                                offering=course, 
                                                position=position,
                                                group=False)
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

                CalLetterActivity.objects.create(name=form.cleaned_data['name'],
                                                short_name=form.cleaned_data['short_name'],
                                                status=form.cleaned_data['status'],
                                                url=form.cleaned_data['url'],
                                                numeric_activity=NumericActivity.objects.get(pk=form.cleaned_data['numeric_activity']),
                                                exam_activity=exam_activity,
                                                offering=course, 
                                                position=position,
                                                group=False)
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
    
    if request.method == 'POST': # If the form has been submitted...
        activity_entries = []
        faked_activities = [] # used to evaluate the formula
        has_error = False
        for numeric_activity in numeric_activities:
            activity_form_entry = ActivityFormEntry(request.POST, prefix=numeric_activity.slug)
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
            

        formula_form_entry = FormulaFormEntry(request.POST)
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
        except EvalException as e:
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

        from_page = request.GET.get('from_page')
        
        if request.method == 'POST': # If the form has been submitted...
            if isinstance(activity, CalNumericActivity):
                form = CalNumericActivityForm(request.POST) # A form bound to the POST data
            elif isinstance(activity, NumericActivity):
                form = NumericActivityForm(request.POST) # A form bound to the POST data
            elif isinstance(activity, CalLetterActivity):
                form = CalLetterActivityForm(request.POST) # A form bound to the POST data
                form.fields['numeric_activity'].choices = numact_choices
                form.fields['exam_activity'].choices = examact_choices
            elif isinstance(activity, LetterActivity):
                form = LetterActivityForm(request.POST) # A form bound to the POST data

            form.activate_editform_validation(course_slug, activity_slug)
            
            if  form.is_valid(): # All validation rules pass                	
                _populate_activity_from_formdata(activity, form.cleaned_data)
                
                activity.save()
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
                                                        kwargs={'course_slug': course_slug, 'activity_slug': activity_slug}))
            else:
                messages.error(request, "Please correct the error below")
        else:
            datadict = _create_activity_formdatadict(activity)
            if isinstance(activity, CalNumericActivity):
                form = CalNumericActivityForm(datadict)
            elif isinstance(activity, NumericActivity):
                form = NumericActivityForm(datadict)
            elif isinstance(activity, CalLetterActivity):
                form = CalLetterActivityForm(datadict)
                form.fields['numeric_activity'].choices = numact_choices
                form.fields['exam_activity'].choices = examact_choices
                # set initial value in form to current value
            elif isinstance(activity, LetterActivity):
                form = LetterActivityForm(datadict)
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
    
        activity.deleted = True
        activity.save()
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
            activity.save()
            messages.success(request, 'Activity made visible to students (but grades are still unreleased).')

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("activity %s made visible") % (activity),
                  related_object=course)
            l.save()
        elif activity.status == "URLS":
            activity.status = "RLS"
            activity.save()
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
                a = LetterActivity.objects.create(name=form.cleaned_data['name'],
                                                short_name=form.cleaned_data['short_name'],
                                                status=form.cleaned_data['status'],
                                                due_date=form.cleaned_data['due_date'],
                                                percent=form.cleaned_data['percent'],
                                                url=form.cleaned_data['url'],
                                                offering=course, position=position,
                                                group=GROUP_STATUS_MAP[form.cleaned_data['group']])
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

#@requires_course_staff_by_slug
#def delete_activity_review(request, course_slug, activity_slug):
#    course = get_object_or_404(CourseOffering, slug=course_slug)
#    activities = all_activities_filter(offering=course, slug=activity_slug)
#    if (len(activities) == 1):
#        activity = activities[0]
#        if isinstance(activity, CalNumericActivity):
#            activity_type = ACTIVITY_TYPE['CNG']
#        elif isinstance(activity, NumericActivity):
#            activity_type = ACTIVITY_TYPE['NG']
#        elif isinstance(activity, LetterActivity):
#            activity_type = ACTIVITY_TYPE['LG']
#        context = {'course': course, 'activity_type': activity_type, 'activity': activities[0]}
#        return render_to_response('grades/delete_activity_review.html', context, context_instance=RequestContext(request))
#    else:
#        return NotFoundResponse(request)

#@requires_course_staff_by_slug
#def delete_activity_confirm(request, course_slug, activity_slug):
#    course = get_object_or_404(CourseOffering, slug=course_slug)
#    activity = get_object_or_404(Activity, offering=course, slug=activity_slug)
#    activity.deleted = True
#    activity.save()
#    #LOG EVENT#
#    l = LogEntry(userid=request.user.username,
#          description=("deleted %s") % (activity),
#          related_object=activity)
#    l.save()
#    return HttpResponseRedirect(reverse('grades.views.course_info', kwargs={'course_slug': course_slug}))

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
    
    context = {'course': course, 'students': students, 'activities': activities, 'grades': grades}
    return render_to_response('grades/all_grades.html', context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def all_grades_csv(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
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
    
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s.csv' % (course_slug)
    
    writer = csv.writer(response)
    row = ['Last name', 'First name', 'Userid', 'Student ID']
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
                       g=gr.letter_grade
            except KeyError:
                g = ''
            row.append(g)
        writer.writerow(row)
        
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
    print groups
    
    rows = []
    for m in members:
        data = {'member': m, 'groups': groups.get(m.id, [])}
        rows.append(data)
    
    context = {'course': course, 'rows': rows}
    return render_to_response('grades/class_list.html', context, context_instance=RequestContext(request))


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
        sub, components = get_current_submission(member.person, a)
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

    context = {'course': course, 'member': member, 'grade_info': grade_info, 'group_memberships': group_memberships}
    return render_to_response('grades/student_info.html', context, context_instance=RequestContext(request))


