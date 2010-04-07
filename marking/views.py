from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from coredata.models import *
from courselib.auth import requires_course_staff_by_slug, is_course_staff_by_slug, is_course_student_by_slug, ForbiddenResponse
from grades.models import NumericActivity
from groups.models import Group
from log.models import *
from models import *      
from forms import *
from django.forms.models import modelformset_factory
from contrib import messages
from django.db.models import Q


def _find_setup_conflicts(source_setup, target_setup):    
    names_found = set()
    short_names_found = set()
    names_found.update((activity.name for activity in source_setup))
    short_names_found.update((activity.short_name for activity in source_setup))
    conflicting_activities = set()
    
    for activity in target_setup:
        if (activity.name in names_found) or (activity.short_name in short_names_found):
            if(activity not in conflicting_activities):
                conflicting_activities.add(activity)
    
    return conflicting_activities

def _check_and_save_renamed_activities(all_activities, conflicting_activities, rename_forms):
    """        
    this function check that if it's ok to rename the activities(which conflict with ones in
    the source course setup) using the new names or new short names in the form.
    if so, update these activities by saving their new name or short names into database    
    """
    names_found = set()
    short_names_found = set()
    names_found.update((act.name for act in all_activities if act not in conflicting_activities))
    short_names_found.update((act.short_name for act in all_activities if act not in conflicting_activities))
    activities_renamed = []
    
    for form in rename_forms:
        if not form.is_valid():
            return 'Error found'
        if form.cleaned_data['selected']:# this conflicting activity is to be renamed
            new_name = form.cleaned_data['name']
            new_short_name = form.cleaned_data['short_name'] 
            if new_name =='' or new_short_name == '':
                return "Name and short name cannot be empty"
            if new_name in names_found:
                return 'Conflicts on name "%s" among the activities in this course' % new_name
            if new_short_name in short_names_found:
                return 'Conflicts on short name "%s" among the activities in this course' % new_short_name
            names_found.add(new_name)
            short_names_found.add(new_short_name)
            act = all_activities.get(id=form.prefix)
            act.name = new_name
            act.short_name = new_short_name
            act.slug = None #set to None for regeneration
            activities_renamed.append(act) 
        else:# this conflicting activity is not to be renamed, add its name and short name to the set 
            act = all_activities.get(id=form.prefix)
            names_found.add(act.name)
            short_names_found.add(act.short_name)             
            
    for act in activities_renamed:
        act.save()
    return None


@requires_course_staff_by_slug
def copy_course_setup(request, course_slug):
    userid = request.user.username  
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    # get the course offerings of this user except for this course
    courses_qset = Member.objects.exclude(role__in=["DROP","STUD"]).exclude(offering=course) \
            .filter(offering__graded=True, person__userid=userid) \
            .select_related('offering','offering__semester')
   
    from django import forms
    class CourseChoiceField(forms.ModelChoiceField):
        def label_from_instance(self, obj):
            return "%s" % (obj.offering)
    class CourseSourceForm(forms.Form):
        course = CourseChoiceField(queryset = courses_qset)    
    
    if request.method == "POST":         
        target_setup = Activity.objects.filter(offering = course)
        error_info = None        
        source_slug = request.GET.get('copy_from')       
        if source_slug == None: # POST request for selecting the source course to copy from
            select_form = CourseSourceForm(request.POST, prefix = "select-form")
            if select_form.is_valid():
                source_course = select_form.cleaned_data['course'].offering
                source_setup = Activity.objects.filter(offering = source_course) 
                conflicting_acts = _find_setup_conflicts(source_setup, target_setup)
                rename_forms =[ ActivityRenameForm(prefix=act.id) for act in conflicting_acts ]
            else:
                 return render_to_response("marking/select_course_setup.html", 
                             {'course': course, 'select_form': select_form},\
                             context_instance=RequestContext(request))                
            
        else: # POST request for renaming and copy    
            source_course = get_object_or_404(CourseOffering, slug = source_slug)
            source_setup = Activity.objects.filter(offering = source_course)  
            conflicting_acts = _find_setup_conflicts(source_setup, target_setup)   
            
            if conflicting_acts: # check the renamed activities
                rename_forms = [ ActivityRenameForm(request.POST, prefix=act.id) for act in conflicting_acts ]
                error_info = _check_and_save_renamed_activities(target_setup, conflicting_acts, rename_forms)
            
            if not error_info:# do the copy !
                copyCourseSetup(source_course, course)
                messages.add_message(request, messages.SUCCESS, \
                        "Course Setup copied from %s (%s)" % (source_course.name(), source_course.semester.label(),))
                return HttpResponseRedirect(reverse('grades.views.course_info', args=(course_slug,)))
        
        if error_info:
            messages.add_message(request, messages.ERROR, error_info)   
        
        return render_to_response("marking/copy_course_setup.html",\
                {'course' : course, 'source_course' : source_course,\
                'source_setup' : source_setup, 'conflicting_activities' : zip(conflicting_acts, rename_forms)},\
                context_instance=RequestContext(request))
            
    else: # for GET request
        select_form = CourseSourceForm(prefix = "select-form")   
        return render_to_response("marking/select_course_setup.html", 
                                 {'course': course, 'select_form': select_form},\
                                 context_instance=RequestContext(request))

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
    total_mark = 0;
    for form in formset.forms:
        try:  # title is required, empty title triggers KeyError and don't consider this row
            form.cleaned_data['title']
        except KeyError:
            continue
        else:
            instance = form.save(commit = False)
            instance.numeric_activity = activity
            if not instance.deleted:
                total_mark += instance.max_mark
            instance.save()
    return total_mark      

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
            if formset.non_form_errors(): # not caused by error of an individual form
                error_info = formset.non_form_errors()[0] 
        else:          
            # save the formset  
            now_max = _save_components(formset, activity)
            messages.add_message(request, messages.SUCCESS, 'Components of %s Saved!' % activity.name)
            # if the max grade changed
            if now_max != activity.max_grade: 
                old_max = activity.max_grade
                activity.max_grade = now_max
                activity.save()               
                messages.add_message(request, messages.WARNING, \
                                     "The max grade of %s updated from %s to %s" % (activity.name, old_max, now_max))
           
        return HttpResponseRedirect(reverse('grades.views.activity_info', \
                                                args=(course_slug, activity_slug)))                   
    else: # for GET request
        formset = ComponentsFormSet(activity, queryset = qset) 
    
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
    # get the components of this activity
    components = activity.activitycomponent_set.filter(deleted = False)
    # only need the common problems associated with these components 
    qset =  CommonProblem.objects.filter(activity_component__in=components, deleted=False);   
                 
    if request.method == "POST":     
        formset = CommonProblemFormSet(components, request.POST, queryset = qset)
        
        if not formset.is_valid(): 
            if formset.non_form_errors(): # not caused by error of an individual form
                error_info = formset.non_form_errors()[0] 
        else:       
            # save the formset  
            _save_common_problems(formset)
            messages.add_message(request, messages.SUCCESS, 'Common problems Saved')
            return HttpResponseRedirect(reverse('grades.views.activity_info', \
                                                args=(course_slug, activity_slug)))                   
    else: # for GET request     
        formset = CommonProblemFormSet(components, queryset = qset) 
    
    if error_info:
        messages.add_message(request, messages.ERROR, error_info)    
    return render_to_response("marking/common_problems.html", 
                              {'course' : course, 'activity' : activity, 
                              'components': components, 'formset' : formset },\
                              context_instance=RequestContext(request))

@requires_course_staff_by_slug
def manage_component_positions(request, course_slug, activity_slug): 
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)
    components =  ActivityComponent.objects.filter(numeric_activity = activity, deleted=False); 
    
    if request.method == 'POST':
        if request.is_ajax():
            component_ids = request.POST.getlist('ids[]') 
            position = 1;
            for id in component_ids:
                comp = get_object_or_404(components, id = id)
                comp.position = position
                comp.save()
                position += 1
            return HttpResponse("Order of components updated !")
           
    return render_to_response("marking/component_positions.html",
                              {'course' : course, 'activity' : activity,\
                               'components': components, 'components': components},\
                               context_instance=RequestContext(request))
    
    
def _initialize_component_mark_forms(components, base_activity_mark=None):
    
    leng = len(components)
    component_mark_forms = []
    
    if base_activity_mark == None:
        for i in range(leng):
            component_mark_forms.append(ActivityComponentMarkForm(prefix = "cmp-form-%s" % (i+1)))    
    else:    
        component_mark_dict = {}
        component_marks = ActivityComponentMark.objects.filter(activity_mark = base_activity_mark) 
        for c_mark in component_marks:
            component_mark_dict[c_mark.activity_component.title] = c_mark    
       
        i = 0
        for i in range(leng):
            component = components[i]
            if component_mark_dict.has_key(component.title):
                c_mark = component_mark_dict[component.title]            
                component_mark_forms.append(ActivityComponentMarkForm(\
                              prefix = "cmp-form-%s" % (i+1), instance = c_mark))            
            else:
                component_mark_forms.append(ActivityComponentMarkForm(\
                              prefix = "cmp-form-%s" % (i+1))) 
   
    return component_mark_forms 

def _construct_mark_components(components, component_mark_forms):
    assert len(components)==len(component_mark_forms)
    mark_components = []
    for i in range(len(components)):
        # select common problems belong to each component
        common_problems = CommonProblem.objects.filter(activity_component = components[i], deleted = False)
        comp = {'component' : components[i], 'form' : component_mark_forms[i], 'common_problems' : common_problems}        
        mark_components.append(comp)
    
    return mark_components              
    
def _check_component_marks_forms(components, component_mark_forms, warnings_to_return):
    """
    return a list of ActivityComponentMark objects generated from the forms 
    if error found in any of the forms, return None
    """
    assert len(components)==len(component_mark_forms)
    cmp_marks = []
    for i in range(len(components)):  
        form = component_mark_forms[i]     
        if not form.is_valid():
            return None
        cmp_mark = form.save(commit = False)
        cmp_mark.activity_component = components[i]                
        cmp_marks.append(cmp_mark)
        if cmp_mark.value < 0:
            warnings_to_return.append("Negative mark given on %s" % components[i].title)
        elif cmp_mark.value > components[i].max_mark:
            warnings_to_return.append("Bonus mark given on %s" % components[i].title)
                
    return cmp_marks

def _check_additional_info_form(addtional_info_form, warnings_to_return):
    """ 
    Return the ActivityMark object containing additional information
    if error found return None
    """
    if addtional_info_form.is_valid():        
        return addtional_info_form.save(commit = False)   
    return None
    
def _compute_final_mark(component_marks, max_grade, additional_info):
    components_total = 0
    for cmp_mark in component_marks:   
        components_total += cmp_mark.value
   
    return  components_total - \
            additional_info.late_penalty * max_grade/100 + \
            additional_info.mark_adjustment

def _save_marking_results(activity, activity_mark, final_mark, marker_ident, mark_receiver_ident, component_marks = None, additional_info=None):
    
    # copy the additional info      
    if additional_info != None:
        activity_mark.copyFrom(additional_info)
    activity_mark.setMark(final_mark)           
    activity_mark.created_by = marker_ident    
    #save the ActivityMark first    
    activity_mark.save()
    
    #save the individual ComponentMarks   
    if component_marks != None:
        for cmp_mark in component_marks:                
            cmp_mark.activity_mark = activity_mark
            cmp_mark.save()
       
    #LOG EVENT#
    l = LogEntry(userid=marker_ident, \
       description="edited grade on %s for %s changed to %s" % \
      (activity, mark_receiver_ident, final_mark), related_object=activity_mark)                     
    l.save()   
     
   
# request to marking view may comes from different pages
FROMPAGE = {'course': 'course', 'activityinfo': 'activityinfo', 'activityinfo_group' : 'activityinfo_group'}
def _marking_redirct_response(request, course_slug, activity_slug):   
    from_page = request.GET.get('from_page')
    if from_page == FROMPAGE['course']:
        redirect_url = reverse('grades.views.course_info', args=(course_slug,))
    elif from_page == FROMPAGE['activityinfo']:
        redirect_url = reverse('grades.views.activity_info', args=(course_slug, activity_slug))
    elif from_page == FROMPAGE['activityinfo_group']:
        redirect_url = reverse('grades.views.activity_info_with_groups', args=(course_slug, activity_slug))
    else: #default to the activity_info page
        redirect_url = reverse('grades.views.activity_info', args=(course_slug, activity_slug))
    
    return HttpResponseRedirect(redirect_url)  
     
 
@requires_course_staff_by_slug
def marking_student(request, course_slug, activity_slug, userid):
    student = get_object_or_404(Person, userid = userid)
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)     
    membership = get_object_or_404(Member, offering = course, person = student, role = 'STUD') 
    
    components = ActivityComponent.objects.filter(numeric_activity = activity, deleted = False)
    component_forms = []
        
    if request.method == 'POST': 
        warning_messages = []
        for i in range(len(components)):
            component_forms.append(ActivityComponentMarkForm(request.POST, prefix = "cmp-form-%s" % (i+1)))        
        additional_info_form = ActivityMarkForm(request.POST, request.FILES, prefix = "additional-form")
        
        component_marks = _check_component_marks_forms(components, component_forms, warning_messages)                
        additional_info = _check_additional_info_form(additional_info_form, warning_messages)
        
        if component_marks != None and additional_info != None:      
            try:            
                ngrade = NumericGrade.objects.get(activity = activity, member = membership)
            except NumericGrade.DoesNotExist: 
                ngrade = NumericGrade(activity = activity, member = membership)
                ngrade.save(newsitem=False)    
            activity_mark = StudentActivityMark(numeric_grade = ngrade)  
            final_grade = _compute_final_mark(component_marks, activity.max_grade, additional_info) 
            _save_marking_results(activity, activity_mark, final_grade, 
                                  request.user.username, ('student %s'% userid),
                                  component_marks, additional_info)
            #LOG EVENT#
#            print "go to log event grade"
#            l = LogEntry(userid=request.user.username,
#            description="changed %s's mark for %s to %s " % (userid, activity, final_grade),
#            related_object=ngrade )
#            l.save()
            messages.add_message(request, messages.SUCCESS, 'Mark for student %s on %s saved!' % (userid, activity.name,))
            for warning in warning_messages:
                messages.add_message(request, messages.WARNING, warning)                      
            return _marking_redirct_response(request, course_slug, activity_slug)
        else:
            messages.add_message(request, messages.ERROR, 'Error found')            
    else: # for GET request
        base_act_mark = None
        act_mark_id = request.GET.get('base_activity_mark')
        if act_mark_id != None:
            base_act_mark = get_activity_mark_by_id(activity, membership, act_mark_id)            
            if base_act_mark == None:
                raise Http404('No such ActivityMark for student %s on %s found.' % (userid, activity))        
        component_forms = _initialize_component_mark_forms(components, base_act_mark)
        additional_info_form = ActivityMarkForm(prefix = "additional-form", instance = base_act_mark)  
    
    mark_components = _construct_mark_components(components, component_forms)   
    return render_to_response("marking/marking.html",
                       {'course':course, 'activity' : activity,'student' : student,                              
                       'additional_info_form' : additional_info_form, 'mark_components': mark_components }, \
                       context_instance=RequestContext(request))  

@requires_course_staff_by_slug
def marking_group(request, course_slug, activity_slug, group_slug):    
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)
    group = get_object_or_404(Group, courseoffering = course, slug = group_slug)
    
    components = ActivityComponent.objects.filter(numeric_activity = activity, deleted = False)
    component_forms = []
        
    if request.method == 'POST': 
        warning_messages = []
        for i in range(len(components)):
            component_forms.append(ActivityComponentMarkForm(request.POST, prefix = "cmp-form-%s" % (i+1)))        
        additional_info_form = ActivityMarkForm(request.POST, request.FILES, prefix = "additional-form")
        
        component_marks = _check_component_marks_forms(components, component_forms, warning_messages)                
        additional_info = _check_additional_info_form(additional_info_form, warning_messages)
        
        if component_marks != None and additional_info != None:          
            activity_mark = GroupActivityMark(group = group, numeric_activity = activity)  
            final_grade =  _compute_final_mark(component_marks, activity.max_grade, additional_info) 
            _save_marking_results(activity, activity_mark, final_grade, 
                                  request.user.username, ('group %s'% group.name),
                                  component_marks, additional_info)
            
            messages.add_message(request, messages.SUCCESS, 'Mark for group %s on %s saved!' % (group.name, activity.name,))                      
            for warning in warning_messages:
                messages.add_message(request, messages.WARNING, warning)
            return _marking_redirct_response(request, course_slug, activity_slug)
        else:
            messages.add_message(request, messages.ERROR, 'Error found')            
    
    else: # for GET request 
        base_act_mark = None
        act_mark_id = request.GET.get('base_activity_mark')
        if act_mark_id != None:
            base_act_mark = get_group_mark_by_id(activity, group, act_mark_id) 
            if base_act_mark == None:
                raise Http404('No such ActivityMark for group %s on %s found.' % (group.name, activity))   
        component_forms = _initialize_component_mark_forms(components, base_act_mark)
        additional_info_form = ActivityMarkForm(prefix = "additional-form", instance = base_act_mark)  
    
    mark_components = _construct_mark_components(components, component_forms)   
    return render_to_response("marking/marking.html",
                       {'course':course, 'activity' : activity,'group' : group,                              
                       'additional_info_form' : additional_info_form, 'mark_components': mark_components }, \
                       context_instance=RequestContext(request))



@login_required
def mark_summary_student(request, course_slug, activity_slug, userid):
     if is_course_staff_by_slug(request.user, course_slug):
        is_staff = True
     elif is_course_student_by_slug(request.user, course_slug):
        is_staff = False
     else:
         return ForbiddenResponse(request)
    
     student = get_object_or_404(Person, userid = userid)
     course = get_object_or_404(CourseOffering, slug = course_slug)    
     activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)     
     membership = get_object_or_404(Member,offering = course, person = student, role = 'STUD')
     
     if not is_staff and userid != request.user.username:
         return ForbiddenResponse(request)
     
     act_mark_id = request.GET.get('activity_mark')
     if act_mark_id != None: # if act_mark_id specified in the url
         act_mark = get_activity_mark_by_id(activity, membership, act_mark_id) 
     else:
         act_mark = get_activity_mark_for_student(activity, membership)
     
     if act_mark == None:
        raise Http404('No such ActivityMark for student %s on %s found.' % (student.userid, activity))
    
     group = None
     if hasattr(act_mark, 'group'):
        group = act_mark.group
                      
     component_marks = ActivityComponentMark.objects.filter(activity_mark = act_mark)      
    
     return render_to_response("marking/mark_summary.html", 
                               {'course':course, 'activity' : activity, 'student' : student, 'group' : group, \
                                'activity_mark': act_mark, 'component_marks': component_marks, \
                                'is_staff': is_staff, 'view_history': act_mark_id == None}, \
                                context_instance = RequestContext(request))

@requires_course_staff_by_slug     
def mark_summary_group(request, course_slug, activity_slug, group_slug):
     if is_course_staff_by_slug(request.user, course_slug):
        is_staff = True
     elif is_course_student_by_slug(request.user, course_slug):
        is_staff = False
     else:
        return ForbiddenResponse(request)
    
     course = get_object_or_404(CourseOffering, slug = course_slug)    
     activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)    
     group = get_object_or_404(Group, courseoffering = course, slug = group_slug)
     
     if not is_staff:
         gm = GroupMember.objects.filter(group=group, student__person__userid=request.user.userid)
         if not gm:
             return ForbiddenResponse(request)
     
     act_mark_id = request.GET.get('activity_mark')
     if act_mark_id != None: 
         act_mark = get_group_mark_by_id(activity, group_slug, act_mark_id)
     else:
         act_mark = get_group_mark(activity, group)
     if act_mark == None:
         raise Http404('No such ActivityMark for group %s on %s found.' % (group.name, activity))
     component_marks = ActivityComponentMark.objects.filter(activity_mark = act_mark)
     
     return render_to_response("marking/mark_summary.html", 
                               {'course':course, 'activity' : activity, 'group' : group, \
                                'activity_mark': act_mark, 'component_marks': component_marks, \
                                'is_staff': is_staff, 'view_history': act_mark_id == None},\
                                context_instance = RequestContext(request))
         
from os import path
from courses.settings import MEDIA_ROOT
@requires_course_staff_by_slug
def download_marking_attachment(request, course_slug, activity_slug, filepath):
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)       
   
    filepath = path.join(MEDIA_ROOT, filepath).replace("\\", "/")
    bytes = path.getsize(filepath)
    download_file = file(filepath, 'r')
   
    response = HttpResponse(download_file.read())
    response['Content-Disposition'] = 'attachment;'
    response['Content-Length'] = bytes
    return response

@requires_course_staff_by_slug
def mark_history_student(request, course_slug, activity_slug, userid):
    """
    show the marking history for the student on the activity
    """
    student = get_object_or_404(Person, userid=userid)
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)     
    membership = get_object_or_404(Member, offering = course, person = student, role = 'STUD') 
    
    context = {'course': course, 'activity' : activity, 'student' : student,}
    mark_history_info = get_activity_mark_for_student(activity, membership, True)
    context.update(mark_history_info)    
    return render_to_response("marking/mark_history_student.html", context, context_instance = RequestContext(request))

@requires_course_staff_by_slug
def mark_history_group(request, course_slug, activity_slug, group_slug):
    """
    show the marking history for the group on the activity
    """
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)     
    group = get_object_or_404(Group, courseoffering = course, slug = group_slug) 
    
    context = {'course': course, 'activity' : activity, 'group' : group,}
    mark_history_info = get_group_mark(activity, group, True)
    context.update(mark_history_info)    
    return render_to_response("marking/mark_history_group.html", context, context_instance = RequestContext(request))
    
import csv
@requires_course_staff_by_slug
def export_csv(request, course_slug, activity_slug):    
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)   
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s_%s.csv' % (course_slug, activity_slug,)

    writer = csv.writer(response)   
    writer.writerow(['Student ID', 'Student Name', 'Grade'])
    
    student_members = Member.objects.filter(offering = course, role = 'STUD')
    for std in student_members:
        row = [std.person.emplid, std.person.name()]
        try: 
            ngrade = NumericGrade.objects.get(activity = activity, member = std)                  
        except NumericGrade.DoesNotExist: #if the  NumericalGrade does not exist yet,
            row.append('no grade')
        else:
            if ngrade.flag == 'GRAD':
               row.append(ngrade.value)   
            else:
               row.append(ngrade.flag)
        writer.writerow(row)

    return response

@requires_course_staff_by_slug
def mark_all_groups(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(NumericActivity, offering=course, slug=activity_slug)
    
    error_info = None
    rows=[]
    warning_info=[]
    groups = set()
    all_members = GroupMember.objects.select_related('group').filter(activity = activity, confirmed = True)
    for member in all_members:
        if not member.group in groups:
            groups.add(member.group)
    
    if request.method == 'POST':
        current_act_marks = []
        for group in groups:
            entry_form = MarkEntryForm(data = request.POST, prefix = group.name)
            if entry_form.is_valid() == False:
                error_info = "Error found"           
            act_mark = get_group_mark(activity, group)         
            if act_mark == None:
                current_mark = 'no grade'
            else:
                current_mark = act_mark.mark 
            current_act_marks.append(act_mark)
            rows.append({'group': group, 'current_mark' : current_mark, 'form' : entry_form})  
        
        if error_info == None:
            updated = 0
            i = 0
            for group in groups:
               new_value = rows[i]['form'].cleaned_data['value']
               if new_value== None or\
                  (current_act_marks[i] != None and current_act_marks[i].mark == new_value):
                   continue               
               act_mark = GroupActivityMark(group=group, numeric_activity=activity)
               _save_marking_results(activity, act_mark, new_value, request.user.username,\
                                     ("group %s" % group.name))
               updated += 1     
               if new_value < 0:
                   warning_info.append("Negative mark given to group %s" % group.name)
               elif new_value > activity.max_grade:
                   warning_info.append("Bonus mark given to group %s" % group.name)  
               i += 1
                 
            if updated > 0:
                messages.add_message(request, messages.SUCCESS, "Marks for all groups on %s saved (%s groups' grades updated)!" % (activity.name, updated))
            for warning in warning_info:
                messages.add_message(request, messages.WARNING, warning)                    
            return HttpResponseRedirect(reverse('grades.views.activity_info', args=(course_slug, activity_slug)))     
        
    else: # for GET request
       for group in groups: 
           act_mark = get_group_mark(activity, group)         
           if act_mark == None:
                current_mark = 'no grade'
           else:
                current_mark = act_mark.mark
           entry_form = MarkEntryForm(prefix = group.name)                                    
           rows.append({'group': group, 'current_mark' : current_mark, 'form' : entry_form}) 
    
    return render_to_response("marking/mark_all_group.html",
                          {'course': course, 'activity': activity,'mark_all_rows': rows }, 
                          context_instance = RequestContext(request))
            
    

@requires_course_staff_by_slug
def mark_all_students(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)
   
    rows = []
    fileform = None
    imported_data = {} #may get filled with data from an imported file, a student userid to grade mapping
    error_info = None 
    warning_info = []
    memberships = Member.objects.select_related('person').filter(offering = course, role = 'STUD')    
    
    if request.method == 'POST' and request.GET.get('import') != 'true':      
        forms = []           
        ngrades = []   
        # get data from the mark entry forms
        for member in memberships: 
            student = member.person  
            entry_form = MarkEntryForm(data = request.POST, prefix = student.userid)
            if entry_form.is_valid() == False:
                error_info = "Error found"           
            ngrade = None
            try:
                ngrade = NumericGrade.objects.get(activity = activity, member = member)
            except NumericGrade.DoesNotExist:
                current_grade = 'no grade'
            else:
                current_grade = ngrade.value                    
            ngrades.append(ngrade)            
            forms.append(entry_form)
            rows.append({'student': student, 'current_grade' : current_grade, 'form' : entry_form})    
       
        # save if needed 
        if error_info == None:
            updated = 0                 
            for i in range(len(memberships)):
               student = memberships[i].person  
               ngrade = ngrades[i]
               new_value = forms[i].cleaned_data['value'] 
               # the new mark is blank or the new mark is the same as the old one, do nothing
               if (new_value == None) or (ngrade and ngrade.value == new_value):
                   continue 
               # save data 
               if ngrade == None:
                    ngrade = NumericGrade(activity = activity, member = memberships[i]);
                    ngrade.save(newsitem=False)
               # created a new activity_mark as well
               activity_mark = StudentActivityMark(numeric_grade = ngrade)              
               _save_marking_results(activity, activity_mark, new_value, request.user.username,\
                                     ("student %s" % student.userid))
               updated += 1     
               if new_value < 0:
                   warning_info.append("Negative mark given to %s on %s" %(student.userid, activity.name))
               elif new_value > activity.max_grade:
                   warning_info.append("Bonus mark given to %s on %s" %(student.userid, activity.name))                  
           
            if updated > 0:
                messages.add_message(request, messages.SUCCESS, "Marks for all students on %s saved (%s students' grades updated)!" % (activity.name, updated))
                for warning in warning_info:
                    messages.add_message(request, messages.WARNING, warning)
                    
            return HttpResponseRedirect(reverse('grades.views.activity_info', args=(course_slug, activity_slug)))  
    
    else: 
        if request.method == 'POST': # for import
            fileform = UploadGradeFileForm(request.POST, request.FILES, prefix = 'import-file');
            if fileform.is_valid() and fileform.cleaned_data['file'] != None:
                students = course.members.filter(person__role='STUD')
                error_info = _compose_imported_grades(fileform.cleaned_data['file'], students, imported_data)
                if error_info == None:
                    messages.add_message(request, messages.SUCCESS,\
                                "%s students' grades imported. Please review before submitting." % len(imported_data.keys()))
        # may use the imported file data to fill in the forms       
        for member in memberships: 
            student = member.person              
            try:
                ngrade = NumericGrade.objects.get(activity = activity, member = member)
            except NumericGrade.DoesNotExist:
                current_grade = 'no grade'
            else:
                current_grade = ngrade.value            
            initial_value = imported_data.get(student.userid) 
            if initial_value != None:
                entry_form = MarkEntryForm(initial = {'value': initial_value}, prefix = student.userid)
            else:
                entry_form = MarkEntryForm(prefix = student.userid)                                    
            rows.append({'student': student, 'current_grade' : current_grade, 'form' : entry_form}) 
               
    if error_info:
        messages.add_message(request, messages.ERROR, error_info) 
    if fileform == None:
        fileform = UploadGradeFileForm(prefix = 'import-file')   
    
    return render_to_response("marking/mark_all_student.html",{'course': course, 'activity': activity,\
                              'fileform' : fileform,'too_many': len(rows) >= 100,\
                              'mark_all_rows': rows }, context_instance = RequestContext(request))
 
def _compose_imported_grades(file, students_qset, data_to_return):
    
    reader = csv.reader(file)   
    try:  
        read = 1;
        for row in reader:            
            try: #if the first row is not an integer, cannot be emplid
                num = int(row[0])                
            except:
                target = students_qset.filter(userid = row[0])
            else:        
                target = students_qset.filter(Q(userid = row[0]) | Q(emplid = num))
            if target.count() == 0:                
                data_to_return.clear()
                return "Error found in file (row %s): Unmatched student number or user-id (%s)." % (read, row[0],)            
            # try to parse the second row as a float           
            value = float(row[1])
            if(data_to_return.has_key(target[0].userid)):
                data_to_return.clear()
                return "Error found in file (row %s): multiple entries found for student (%s)." % (read, row[0],) 
            data_to_return[target[0].userid] = value 
            read += 1               
    except:
        data_to_return.clear()
        return ("Error found in the file (row %s): The format should be " % read) +\
               "\"[student user-id or student number,  grade, ]\" and " + \
               "only the first two columns are used."   
    return None   

        
        
