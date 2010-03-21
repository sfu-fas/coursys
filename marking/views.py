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

@requires_course_staff_by_slug
def list_activities(request, course_slug):
    target_userid = request.user.username  
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    # get the numeric activities for this course_offering 
    activities = NumericActivity.objects.filter(offering = course)
      
    person = get_object_or_404(Person, userid = request.user.username)
    # get the course offerings of this user
    courses_qset = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=target_userid) \
            .select_related('offering','offering__semester')     
    
    from django import forms
    class CourseReceiverForm(forms.Form):
        course = forms.ModelChoiceField(queryset = courses_qset) 
        
    if request.method == "POST": 
        course_receiver_form = CourseReceiverForm(request.POST, prefix = "course-receiver-form")
        if course_receiver_form.is_valid():
            course_copy_from = course_receiver_form.cleaned_data['course'].offering
            course_copy_to = course
            copyCourseSetup(course_copy_from, course_copy_to)
            return HttpResponseRedirect(reverse('grades.views.course_info', \
                                                args=(course_slug,)))
    else:      
        course_receiver_form = CourseReceiverForm(prefix = "course-receiver-form")  
        return render_to_response("marking/activities.html", {'course': course, 'course_receiver_form': course_receiver_form, \
                                                              'activities' : activities}, context_instance=RequestContext(request))

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
            if not any(formset.errors): # not caused by error of an individual form
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
                              'formset' : formset },\
                              context_instance=RequestContext(request))
    
def _initialize_component_mark_forms(components, base_activity_mark=None):
    
    leng = len(components)
    component_mark_forms = []
    
    if base_activity_mark == None:
        for i in range(leng):
            component_mark_forms.append(ActivityComponentMarkForm(max_mark = components[i].max_mark, \
                                  prefix = "cmp-form-%s" % (i+1)))    
    else:    
        component_mark_dict = {}
        component_marks = ActivityComponentMark.objects.select_related().filter(activity_mark = base_activity_mark) 
        for c_mark in component_marks:
            component_mark_dict[c_mark.activity_component.title] = c_mark    
        i = 0
        for i in range(leng):
            component = components[i]
            if component_mark_dict.has_key(component.title):
                c_mark = component_mark_dict[component.title]            
                component_mark_forms.append(ActivityComponentMarkForm(max_mark = component.max_mark, \
                              prefix = "cmp-form-%s" % (i+1), instance = c_mark))            
            else:
                component_mark_forms.append(ActivityComponentMarkForm(max_mark = component.max_mark, \
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
    
def _check_component_marks_forms(components, component_mark_forms):
    """
    return a list of ActivityComponentMark objects generated from the forms 
    if error found in any of the forms, return None
    """
    assert len(components)==len(component_mark_forms)
    cmp_marks = []
    for i in range(len(components)):  
        form = component_mark_forms[i]     
        if not form.is_valid():
            print form.errors
            return None
        cmp_mark = form.save(commit = False)
        cmp_mark.activity_component = components[i]                
        cmp_marks.append(cmp_mark)
                
    return cmp_marks

def _check_additional_info_form(addtional_info_form):
    """ 
    Return the ActivityMark object containing additional information
    if error found return None
    """
    if addtional_info_form.is_valid():        
        return addtional_info_form.save(commit = False)    
    print addtional_info_form.as_p()
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
       
    #add to log 
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
        for i in range(len(components)):
            component_forms.append(ActivityComponentMarkForm(components[i].max_mark, request.POST, prefix = "cmp-form-%s" % (i+1)))        
        additional_info_form = ActivityMarkForm(request.POST, request.FILES, prefix = "additional-form")
        
        component_marks = _check_component_marks_forms(components, component_forms)                
        additional_info = _check_additional_info_form(additional_info_form)
        
        if component_marks != None and additional_info != None:      
            try:            
                ngrade = NumericGrade.objects.get(activity = activity, member = membership)
            except NumericGrade.DoesNotExist: 
                ngrade = NumericGrade(activity = activity, member = membership)
                ngrade.save()    
            activity_mark = StudentActivityMark(numeric_grade = ngrade)  
            final_grade =  _compute_final_mark(component_marks, activity.max_grade, additional_info) 
            _save_marking_results(activity, activity_mark, final_grade, 
                                  request.user.username, ('student %s', userid), 
                                  component_marks, additional_info)
            
            messages.add_message(request, messages.SUCCESS, 'Marking for student %s on activity %s finished' % (userid, activity.name,))                      
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
        for i in range(len(components)):
            component_forms.append(ActivityComponentMarkForm(components[i].max_mark, request.POST, prefix = "cmp-form-%s" % (i+1)))        
        additional_info_form = ActivityMarkForm(request.POST, request.FILES, prefix = "additional-form")
        
        component_marks = _check_component_marks_forms(components, component_forms)                
        additional_info = _check_additional_info_form(additional_info_form)
        
        if component_marks != None and additional_info != None:          
            activity_mark = GroupActivityMark(group = group, numeric_activity = activity)  
            final_grade =  _compute_final_mark(component_marks, activity.max_grade, additional_info) 
            _save_marking_results(activity, activity_mark, final_grade, 
                                  request.user.username, ('group %s', group.name), 
                                  component_marks, additional_info)
            
            messages.add_message(request, messages.SUCCESS, 'Marking for group %s on activity %s finished' % (group.name, activity.name,))                      
            return _marking_redirct_response(request, course_slug, activity_slug)
        else:
            messages.add_message(request, messages.ERROR, 'Error found')            
    
    else: # for GET request 
        component_forms = _initialize_component_mark_forms(components)
        additional_info_form = ActivityMarkForm(prefix = "additional-form")  
    
    mark_components = _construct_mark_components(components, component_forms)   
    return render_to_response("marking/marking.html",
                       {'course':course, 'activity' : activity,'group' : group,                              
                       'additional_info_form' : additional_info_form, 'mark_components': mark_components }, \
                       context_instance=RequestContext(request))

@requires_course_staff_by_slug
def mark_summary(request, course_slug, activity_slug, userid):
     student = get_object_or_404(Person, userid = userid)
     course = get_object_or_404(CourseOffering, slug = course_slug)    
     activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)     
     membership = get_object_or_404(Member, offering = course, person = student, role = 'STUD') 
     
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
                                'view_history': act_mark_id == None}, context_instance = RequestContext(request))
     
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
def mark_history(request, course_slug, activity_slug, userid):
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
    return render_to_response("marking/mark_history.html", context, context_instance = RequestContext(request))
    

import csv
@requires_course_staff_by_slug
def export_csv(request, course_slug, activity_slug):    
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)   
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s_%s.csv' % (course_slug, activity_slug,)

    writer = csv.writer(response)   
    writer.writerow(['Student ID', 'Student Name', 'Status', 'Grade'])
    
    student_members = Member.objects.filter(offering = course, role = 'STUD')
    for std in student_members:
        row = [std.person.emplid, std.person.name()]
        try: 
            ngrade = NumericGrade.objects.get(activity = activity, member = std)                  
        except NumericGrade.DoesNotExist: #if the  NumericalGrade does not exist yet,
            row.append('Not Graded')
            row.append('--')
        else:
            row.append(ngrade.flag)
            row.append(ngrade.value)   
        writer.writerow(row)

    return response

@requires_course_staff_by_slug
def mark_all_students(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)
   
    rows = []
    error_found = False 
    memberships = Member.objects.select_related('person').filter(offering = course, role = 'STUD')    
    if request.method == 'POST':
        forms = []   
        ngrades = []   
        # get data from the mark entry forms
        for member in memberships: 
            student = member.person  
            entry_form = MarkEntryForm(max_value = activity.max_grade, data = request.POST, prefix = student.userid)
            if entry_form.is_valid() == False:
                error_found = True           
            ngrade = None
            try:
                ngrade = NumericGrade.objects.get(activity = activity, member = member)
            except NumericGrade.DoesNotExist:
                current_grade = 'Not Graded'
            else:
                current_grade = ngrade.value
                    
            ngrades.append(ngrade)            
            forms.append(entry_form)
            rows.append({'student': student, 'current_grade' : current_grade, 'form' : entry_form})    
       
        # try to save if needed 
        if not error_found:
            updated = 0                 
            for i in range(len(memberships)):
               student = memberships[i].person  
               ngrade = ngrades[i]
               new_value = forms[i].cleaned_data['value'] 
               # the new mark is blank, do nothing
               if new_value == None:
                   continue 
               # the new mark is the same as the old one, do nothing
               if ngrade and ngrade.value == new_value:                 
                   continue
               # save data 
               if ngrade == None:
                    ngrade = NumericGrade(activity = activity, member = memberships[i]);
                    ngrade.save()
               # created a new activity_mark as well
               activity_mark = StudentActivityMark(numeric_grade = ngrade)              
               _save_marking_results(activity, activity_mark, new_value, request.user.username,\
                                     ("student %s" % student.userid))
               updated += 1                        
           
            if updated > 0:
                messages.add_message(request, messages.SUCCESS, "Marking for all students on activity %s saved (%s students' grades updated)!" % (activity.name, updated))
            return HttpResponseRedirect(reverse('grades.views.activity_info', args=(course_slug, activity_slug)))  
                
    else: # for GET request       
        for member in memberships: 
            student = member.person              
            try:
                ngrade = NumericGrade.objects.get(activity = activity, member = member)
            except NumericGrade.DoesNotExist:
                current_grade = 'Not Graded'
            else:
                current_grade = ngrade.value
                    
            entry_form = MarkEntryForm(max_value = activity.max_grade, prefix = student.userid)                           
            rows.append({'student': student, 'current_grade' : current_grade, 'form' : entry_form})   
               
    if error_found:
        messages.add_message(request, messages.ERROR, 'Invalid grade found')   
    
    return render_to_response("marking/mark_all.html",{'course': course, 'activity': activity, 
                              'too_many': len(rows) >= 100, 'mark_all_rows': rows},                              
                              context_instance = RequestContext(request))
     
     
            

    
