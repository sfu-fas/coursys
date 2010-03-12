from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from coredata.models import *
from courselib.auth import requires_faculty_member, requires_course_staff_by_slug
from grades.models import NumericActivity
from groups.models import Group
from log.models import *
from models import *      
from forms import *
from django.forms.models import modelformset_factory
from contrib import messages


@login_required
def index(request):
    target_userid = request.user.username
    person = get_object_or_404(Person, userid = target_userid)
    # get the course offerings of this user
    courses = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=target_userid) \
            .select_related('offering','offering__semester')
    return render_to_response("marking/index.html", {'person':person, 'course_memberships':courses}, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def list_activities(request, course_slug):
    target_userid = request.user.username  
    # get the numeric activities for this course_offering 
    course = get_object_or_404(CourseOffering, slug = course_slug)
    all_activities = course.activity_set.all()
    target_activities = []
    # only show the numeric activities for marking
    for act in all_activities:
        if hasattr(act, 'numericactivity'):
            target_activities.append(act) 
    
    from django import forms
    target_userid = request.user.username
    person = get_object_or_404(Person, userid = target_userid)
    # get the course offerings of this user
    courses_qset = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=target_userid) \
            .select_related('offering','offering__semester') 
    class CourseReceiverForm(forms.Form):
        course = forms.ModelChoiceField(queryset = courses_qset) 
        
    if request.method == "POST": 
        course_receiver_form = CourseReceiverForm(request.POST, prefix = "course-receiver-form")
        if course_receiver_form.is_valid():
            #print 'valid'
            course_copy_from = course_receiver_form.cleaned_data['course'].offering
            course_copy_to = course
            copyCourseSetup(course_copy_from, course_copy_to)
            #print course_copy_from
            #print course_copy_to
            #print 'copied'                              
            return HttpResponseRedirect(reverse('marking.views.list_activities', \
                                                args=(course_slug,)))
    else:      
        course_receiver_form = CourseReceiverForm(prefix = "course-receiver-form")  
        return render_to_response("marking/activities.html", {'course': course, 'course_receiver_form': course_receiver_form, \
                                                              'activities' : target_activities}, context_instance=RequestContext(request))

def _save_common_problems(formset):
    for form in formset.forms:
        try:  # component is required, empty component triggers KeyError and don't consider this row
            form.cleaned_data['activity_component']
        except KeyError:       
            continue
        try:  # title is required, empty title triggers KeyError and don't consider this row
            form.cleaned_data['title']
        except KeyError:            
            continue
        else:
            instance = form.save()

def _save_components(formset, activity):
    position = 1;
    for form in formset.forms:
        try:  # title is required, empty title triggers KeyError and don't consider this row
            form.cleaned_data['title']
        except KeyError:
            continue
        else:
            instance = form.save(commit = False)
            instance.numeric_activity = activity
            if not instance.deleted:
                instance.position = position
                position += 1
            else:
                instance.position = None
            instance.save()      

from django.db.models import Max
def _get_activity_mark(activity, student_membership, activity_mark_id = None, include_all = False):
     """
     this function returns the mark of the student on the activity
     
     if activity_mark_id is specified, return that activity_mark if it 
     exists for the student on the activity(return None otherwise). And here 
     we don't consider the include_all.
    
     if include_all is False, only return the current mark which is latest created 
     and thus currently valid; otherwise not only return the current mark but also the 
     all the history marks for the student on the activity        
     """  
     current_act_mark = None
     std_act_marks = None
     grp_act_marks = None     
     
     print "activity_mark_id %s" % activity_mark_id
     # the mark maybe assigned directly to this student 
     num_grade = get_object_or_404(NumericGrade, activity = activity, member = student_membership)
     std_act_marks = StudentActivityMark.objects.filter(numeric_grade = num_grade)
     latest = None
     if std_act_marks.count() != 0 :
        
        if activity_mark_id != None:
           for act in std_act_marks:             
               if act.id == int(activity_mark_id):
                   print "found"
                   return act    
        
        #get the latest one
        latest = std_act_marks.aggregate(Max('created_at'))['created_at__max']
        current_act_mark = std_act_marks.get(created_at = latest)
        
     # the mark maybe assigned to this student via the group this student participates
     try:   
        group_mem = GroupMember.objects.get(student = student_membership)
     except GroupMember.DoesNotExist:
        pass
     else:
        group = group_mem.group
        grp_act_marks = GroupActivityMark.objects.filter(group = group)    
        if grp_act_marks.count() != 0 : 
           
            if activity_mark_id != None:
                for act in grp_act_marks:
                    if act.id == int(activity_mark_id):
                        print "found"
                        return act
                return None
             
            latest2 = grp_act_marks.aggregate(Max('created_at'))['created_at__max']
            if lateset == None or latest2 > lateset:
                current_act_mark = grp_act_marks.get(created_at = latest2)
        
     if activity_mark_id != None:
         print "not found"
         raise Http404('No such ActivityMark for student %s on %s found.' % (student_membership.person), activity)
    
     if not include_all:
         return current_act_mark
     else:
        all_act_mark = []
        if std_act_marks:
            all_act_mark.extend(std_act_marks)
        if grp_act_marks:
            all_act_mark.extend(grp_act_marks)
        return {'current_activity_mark' : current_act_mark, 
                'all_activity_marks' : all_act_mark,}
     

@requires_course_staff_by_slug
def manage_activity_components(request, course_slug, activity_slug):    
            
    error_info = None
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug) 
   
    fields = ('title', 'description', 'max_mark', 'deleted',)
    
    ComponentsFormSet  = modelformset_factory(ActivityComponent, fields=fields, \
                                              formset=BaseActivityComponentFormSet, \
                                              can_delete = False, extra = 3) 
    
    qset =  ActivityComponent.objects.filter(numeric_activity = activity, deleted=False);
                 
    if request.method == "POST":     
        formset = ComponentsFormSet(activity, request.POST, queryset = qset)
        
        if not formset.is_valid():
            if not any(formset.errors): # not caused by error of an individual form
                error_info = formset.non_form_errors()[0] 
        else:          
            # save the formset  
            _save_components(formset, activity)
            messages.add_message(request, messages.SUCCESS, 'Activity Components Saved')
            return HttpResponseRedirect(reverse('marking.views.list_activities', \
                                                args=(course_slug,)))                   
    else: # for GET
        formset = ComponentsFormSet(queryset = qset) 
    
    if error_info:
        messages.add_message(request, messages.ERROR, error_info)
    return render_to_response("marking/components.html", 
                              {'course' : course, 'activity' : activity,\
                               'formset' : formset },\
                               context_instance=RequestContext(request))
    
@requires_course_staff_by_slug
def manage_common_problems(request, course_slug, activity_slug):    
       
    error_info = None
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug) 
   
    fields = ('activity_component', 'title', 'description', 'penalty', 'deleted',)
    
    CommonProblemFormSet = modelformset_factory(CommonProblem, fields=fields, \
                                              formset=BaseCommonProblemFormSet, \
                                              can_delete = False, extra = 3) 
    
    # only filter out the common problems associated with components of this activity
    components = activity.activitycomponent_set.filter(deleted = False)    
    qset =  CommonProblem.objects.filter(activity_component__in=components, deleted=False);
                 
    if request.method == "POST":     
        formset = CommonProblemFormSet(request.POST, queryset = qset)
        
        if not formset.is_valid():
            if not any(formset.errors): # not caused by error of an individual form
                error_info = formset.non_form_errors()[0] 
        else:       
            # save the formset  
            _save_common_problems(formset)
            messages.add_message(request, messages.SUCCESS, 'Common problems Saved')
            return HttpResponseRedirect(reverse('marking.views.list_activities', \
                                                args=(course_slug,)))                   
    else: # for GET        
        formset = CommonProblemFormSet(queryset = qset) 
    
    if error_info:
        messages.add_message(request, messages.ERROR, error_info)    
    return render_to_response("marking/common_problems.html", 
                              {'course' : course, 'activity' : activity, 
                              'formset' : formset },\
                              context_instance=RequestContext(request))
    
@requires_course_staff_by_slug
def marking(request, course_slug, activity_slug):
        
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)
    
    students_qset = course.members.filter(person__role = 'STUD')
    groups_qset = Group.objects.filter(courseoffering = course)
    
    #init
    student = None
    group = None
    student_receiver_form = None
    group_receiver_form = None
    error_info = ""
    
    from django import forms 
    class MarkStudentReceiverForm(forms.Form):
        student = forms.ModelChoiceField(queryset = students_qset)        
    class MarkGroupReceiverForm(forms.Form):
        group = forms.ModelChoiceField(queryset = groups_qset)    
    
    components = ActivityComponent.objects.filter(numeric_activity = activity, deleted = False)     
    leng = len(components)    
    forms = []    
        
    if request.method == "POST":         
        # the mark receiver(either a student or a group) may included in the url's query part
        std_userid = request.GET.get('student')
        group_id = request.GET.get('group')
        receiver_in_url = (std_userid != None or group_id != None)    
        
        if receiver_in_url == False :
            student_receiver_form = MarkStudentReceiverForm(request.POST, prefix = "student-receiver-form")
            group_receiver_form = MarkGroupReceiverForm(request.POST, prefix = "group-receiver-form")            
            is_student = student_receiver_form.is_valid()
            is_group = group_receiver_form.is_valid()
        elif std_userid:
            is_student = True
            is_group = False
        else:
            is_student = False
            is_group = True
        
        # this should be ensured on the client side
        if is_student and is_group: 
            error_info = "You can only give mark to a student or a group but not both at the same time"               
                        
        if (not is_student) and (not is_group):
            error_info = "Please select the student or group to give the mark to"     
                          
        for i in range(leng):
            forms.append(ActivityComponentMarkForm(request.POST, prefix = "cmp-form-%s" % (i+1)))
        
        cmp_marks = []
        if not error_info:
            total_mark = 0
            for i in range(leng):         
                if not forms[i].is_valid():
                    error_info = "Error found" 
                    break
                cmp_mark = forms[i].save(commit = False)
                cmp_mark.activity_component = components[i]                
                cmp_marks.append(cmp_mark)            
                if cmp_mark.value > components[i].max_mark:
                    error_info = "Mark too high for %s" % components[i].title
                    break;  
                total_mark += cmp_mark.value
                
        additional_info_form = ActivityMarkForm(request.POST, request.FILES, prefix = "additional-form")
        
        if (not additional_info_form.is_valid()) and (not error_info):
            error_info = "Error found in additional information"
            
        # no error, save the result
        if not error_info:             
            if is_student: #get the student
                if receiver_in_url:
                    student = get_object_or_404(Person, userid = std_userid)
                else:
                    student = student_receiver_form.cleaned_data['student']
                membership = get_object_or_404(Member, offering = course, person = student, role = 'STUD')                     
                #get the corresponding NumericGrade object
                try: 
                    ngrade = NumericGrade.objects.get(activity = activity, member = membership)                  
                except NumericGrade.DoesNotExist: #if the  NumericalGrade does not exist yet, create a new one
                    ngrade = NumericGrade(activity = activity, member = membership)                  
                    ngrade.save()                            
                
                activity_mark = StudentActivityMark(numeric_grade = ngrade)            
              
            else:#get the group
                if receiver_in_url:
                    group = objects.get_object_or_404(Group, courseoffering = course, id = group_id)
                else:
                    group = group_receiver_form.cleaned_data['group']
                activity_mark = GroupActivityMark(group = group, numeric_activity = activity)
                        
            #get the additional info
            additional = additional_info_form.save(commit = False)             
            #copy the additional info        
            activity_mark.copyFrom(additional)            
            #assign the mark            
            activity_mark.setMark(total_mark - additional.late_penalty + additional.mark_adjustment)           
            activity_mark.created_by = request.user.username
            activity_mark.save()
            
            #save the individual ComponentMarks
            for cmp_mark in cmp_marks:                
                cmp_mark.activity_mark = activity_mark
                cmp_mark.save()
                 
            #add the log entry 
            receiver = is_student and 'student ' + student.userid or 'group ' + group.name
            l = LogEntry(userid=request.user.username, \
              description="edited grade on %s for %s changed to %s" % \
              (activity, receiver, total_mark), related_object=activity_mark)                     
            l.save()                         
            messages.add_message(request, messages.SUCCESS, 'Marking for %s on activity %s finished' % (receiver, activity.name,))                      
            return HttpResponseRedirect(reverse('marking.views.list_activities', \
                                                args=(course_slug,)))       
    else: # for GET request  
        # the mark receiver(either a student or a group) may included in the url's query part
        std_userid = request.GET.get('student')
        group_id = request.GET.get('group')
        receiver_in_url = (std_userid != None or group_id != None)        
       
        if receiver_in_url == False :                          
            student_receiver_form = MarkStudentReceiverForm(prefix = "student-receiver-form")
            group_receiver_form = MarkGroupReceiverForm(prefix = "group-receiver-form")
            student = None
            group = None
        elif std_userid:
            student = get_object_or_404(Person, userid = std_userid)
        else:
            group = get_object_or_404(Group, id = group_id)
       
        for i in range(leng):
            forms.append(ActivityComponentMarkForm(prefix = "cmp-form-%s" % (i+1)))
        
        additional_info_form = ActivityMarkForm(prefix = "additional-form") 
           
    mark_components = []
    for i in range(leng):
        common_problems = CommonProblem.objects.filter(activity_component = components[i], deleted = False)
        comp = {'component' : components[i], 'form' : forms[i], 'common_problems' : common_problems}        
        mark_components.append(comp)
     
    if error_info:
        messages.add_message(request, messages.ERROR, error_info)
    return render_to_response("marking/marking.html",
                             {'course':course, 'activity' : activity,
                              'student' : student, 'group' : group, \
                              'student_receiver_form' : student_receiver_form, 'group_receiver_form' : group_receiver_form,
                              'additional_info_form' : additional_info_form, 'mark_components': mark_components }, \
                              context_instance=RequestContext(request))
    

@requires_course_staff_by_slug
def mark_summary(request, course_slug, activity_slug):
     student_id = request.GET.get('student')
     student = get_object_or_404(Person, userid = student_id)
     course = get_object_or_404(CourseOffering, slug = course_slug)    
     activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)     
     membership = get_object_or_404(Member, offering = course, person = student, role = 'STUD') 
     
     act_mark_id = request.GET.get('activity_mark')
     print act_mark_id
     if act_mark_id != None: # if act_mark_id specified in the url
         act_mark = _get_activity_mark(activity, membership, act_mark_id)         
     else:
         act_mark = _get_activity_mark(activity, membership)
                         
     component_marks = ActivityComponentMark.objects.filter(activity_mark = act_mark)
    
     return render_to_response("marking/mark_summary.html", 
                               {'course':course, 'activity' : activity, 'student' : student, \
                                'activity_mark': act_mark, 'component_marks': component_marks, \
                                'view_history': act_mark_id == None}, context_instance = RequestContext(request))
     
from os import path, getcwd
@requires_course_staff_by_slug
def download_marking_attachment(request, course_slug, activity_slug, filepath):
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)       
    filepath = path.join(getcwd(), "media", filepath)
    filepath = filepath.replace("\\", "/")
    print filepath
    bytes = path.getsize(filepath)
    download_file = file(filepath, 'r')
    response = HttpResponse(download_file.read())
    response['Content-Disposition'] = 'attachment;'
    response['Content-Length'] = bytes
    return response

@requires_course_staff_by_slug
def mark_history(request, course_slug, activity_slug):
    """
    show the marking history for a student on an activity
    """
    student_id = request.GET.get('student')
    student = get_object_or_404(Person, userid = student_id)
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)     
    membership = get_object_or_404(Member, offering = course, person = student, role = 'STUD') 
    
    context = {'course': course, 'activity' : activity, 'student' : student,}
    context.update(_get_activity_mark(activity = activity, student_membership = membership, include_all = True))
    
    return render_to_response("marking/mark_history.html", context, context_instance = RequestContext(request))
    
    