from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from coredata.models import *
from courselib.auth import requires_faculty_member, requires_course_staff_by_slug
from grades.models import NumericActivity
from models import *
from django.forms.models import modelformset_factory    

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
            
    return render_to_response("marking/activities.html", {'course_slug': course_slug, 'activities' : target_activities}, context_instance=RequestContext(request))


def _check_components_titles(formset):
      titles = []
      for form in formset.forms:
        try: # since title is required, empty title triggers KeyError and don't consider this row
            form.cleaned_data['title']
        except KeyError:
            continue
        else:  
            title = form.cleaned_data['title']
            if (not form.cleaned_data['deleted']) and title in titles:
                return False
            titles.append(title)        
      return True 

def _save_components(formset, activity):
      for form in formset.forms:
        try:  # title is required, empty title triggers KeyError and don't consider this row
            form.cleaned_data['title']
        except KeyError:
            continue
        else:
            instance = form.save(commit = False)
            instance.numeric_activity = activity
            instance.save()
            print "Component %s added" % instance

@requires_course_staff_by_slug
def manage_activity_components(request, course_slug, activity_short_name):    
            
    error_info = ""
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(NumericActivity, offering = course, short_name = activity_short_name) 
   
    fields = ('title', 'description', 'max_mark', 'deleted',)
    fcols = ('Title', 'Description', 'Max Mark', 'Delete?',)    
    
    ComponentsFormSet  = modelformset_factory(ActivityComponent, fields=fields, \
                                              can_delete = False, extra = 5) 
    
    qset =  ActivityComponent.objects.filter(numeric_activity = activity, deleted=False);
                 
    if request.method == "POST":     
        formset_main = ComponentsFormSet(request.POST, queryset = qset)
        
        if formset_main.is_valid() == False:
              error_info = "Some component has error" 
        elif _check_components_titles(formset_main) == False:             
              error_info = "Each component must have an unique title"
        else:          
            # save the main formset first  
            _save_components(formset_main, activity)
            return HttpResponseRedirect(reverse('marking.views.list_activities', \
                                                args=(course_slug,)))                   
    else: # for PUT
        formset_main = ComponentsFormSet(queryset = qset) 
    
    return render_to_response("marking/components.html", 
                              {'course' : course, 'activity' : activity, 'fields_main' : fcols,\
                               'formset_main' : formset_main,'error_info' : error_info,},\
                               context_instance=RequestContext(request))
    
@requires_course_staff_by_slug
def marking(request, course_slug, activity_short_name):
    
    error_info = ""
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(NumericActivity, offering = course, short_name = activity_short_name)    
    
    from django import forms    
    students_qset = course.members.filter(person__offering = course, person__role = "STUD")     
    class MarkReceiverForm(forms.Form):
        student_selection = forms.ModelChoiceField(queryset = students_qset)        
    
    components = ActivityComponent.objects.filter(numeric_activity = activity, deleted = False)     
    leng = len(components)    
    forms = []    
        
    if request.method == "POST":                
        receiver_form = MarkReceiverForm(request.POST, prefix = "receiver-form")
                       
        if not receiver_form.is_valid():
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
                if cmp_mark.value > components[i].max_mark or cmp_mark.value < 0:
                    error_info = "Invalid mark for %s" % components[i].title
                    break;  
                total_mark += cmp_mark.value
                
        additional_info_form = ActivityMarkForm(request.POST, request.FILES, prefix = "additional-form")
        
        if (not error_info) and (not additional_info_form.is_valid()):
            error_info = "Error found"
            
        # no error, save the result
        if not error_info: 
            #get the student and the member
            student = receiver_form.cleaned_data["student_selection"]            
            membership = course.member_set.get(person = student)                     
            #get the corresponding NumericGrade object
            try: 
                ngrade = NumericGrade.objects.get(activity = activity, member = membership)                  
            except NumericGrade.DoesNotExist: #if the  NumericalGrade does not exist yet, create a new one
                ngrade = NumericGrade(activity = activity, member = membership)                  
                ngrade.save()                            
                stu_activity_mark = StudentActivityMark(numeric_grade = ngrade)            
            else:
                #get the corresponding StudentActivityMark object
                try:                     
                    stu_activity_mark = StudentActivityMark.objects.get(numeric_grade = ngrade)   
                except StudentActivityMark.DoesNotExist: #if the  StudentActivityMark does not exist yet, create a new one               
                    stu_activity_mark = StudentActivityMark(numeric_grade = ngrade)
                        
            #get the additional info
            additional = additional_info_form.save(commit = False)             
            #copy the additional info        
            stu_activity_mark.copyAdditionalFrom(additional)            
            #assign the mark 
            stu_activity_mark.setMark(total_mark - additional.late_penalty + additional.mark_adjustment)           
            stu_activity_mark.save()
            
            #save the individual ComponentMarks
            for cmp_mark in cmp_marks:
                cmp_mark.activity_mark = stu_activity_mark
                cmp_mark.save()
                                    
            return HttpResponseRedirect(reverse('marking.views.list_activities', \
                                                args=(course_slug,)))       
    else:                  
        receiver_form = MarkReceiverForm(prefix = "receiver-form")
        for i in range(leng):
            forms.append(ActivityComponentMarkForm(prefix = "cmp-form-%s" % (i+1)))
            print forms[i].as_p()
        additional_info_form = ActivityMarkForm(prefix = "additional-form") 
           
    mark_components = []
    for i in range(leng):
        common_problems = CommonProblem.objects.filter(activity_component = components[i], deleted = False)
        cmp_form = {'component' : components[i], 'form' : forms[i], 'common_problems' : common_problems}        
        mark_components.append(cmp_form)
  
    return render_to_response("marking/marking.html",
                             {'course':course, 'activity' : activity, 'receiver_form' : receiver_form,
                              'additional_info_form' : additional_info_form, 'mark_components': mark_components, \
                              'error_info': error_info, },\
                              context_instance=RequestContext(request))
    
        