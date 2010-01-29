from django.shortcuts import render_to_response
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
    person = Person.objects.get(userid = target_userid)
    # get the course offerings of this user
    courses = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=target_userid) \
            .select_related('offering','offering__semester')
    print courses[0].offering.get_absolute_url()
    return render_to_response("marking/index.html", {'person':person, 'course_memberships':courses}, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def list_activities(request, course_slug):
    print "list_activities %s" % course_slug
    target_userid = request.user.username
    print course_slug
    person = Person.objects.get(userid = target_userid)
    # get the numeric activities for this course_offering    
    course = CourseOffering.objects.get(slug=course_slug)
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
    course = CourseOffering.objects.get(slug = course_slug)    
    activity = NumericActivity.objects.filter(offering = course).get(short_name = activity_short_name) 
   
    fields = ('title', 'description', 'max_mark', 'deleted',)
    fcols = ('Title', 'Description', 'Max Mark', 'Delete?',)    
    
    ComponentsFormSet  = modelformset_factory(ActivityComponent, fields=fields, \
                                              can_delete = False, extra = 5) 
    
    qset =  ActivityComponent.objects.filter(numeric_activity = activity, deleted=False);
                 
    if request.method == "POST":     
        formset_main = ComponentsFormSet(request.POST, queryset = qset)
        print formset_main.as_table
        
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
    course = CourseOffering.objects.get(slug = course_slug)    
    activity = NumericActivity.objects.filter(offering = course).get(short_name = activity_short_name)    
    
    from django import forms    
    students_qset = course.members.filter(person__offering = course, person__role = "STUD")     
    class MarkReceiverForm(forms.Form):
        student_selection = forms.ModelChoiceField(queryset = students_qset)        
    
    components = ActivityComponent.objects.filter(numeric_activity = activity, deleted = False)     
    leng = len(components)    
    forms = []    
        
    if request.method == "POST":
                
        receiver_form = MarkReceiverForm(request.POST, prefix = "receiver-form")
        print receiver_form.errors
        
        if not receiver_form.is_valid():
            error_info = "Please select the student or group to give the mark to"       
        
        for i in range(leng):
            forms.append(ActivityComponentMarkForm(request.POST, prefix = "cmp-form-%s" % (i+1)))
       
        total_mark = 0
        for i in range(leng):         
            if not forms[i].is_valid():
                error_info = "Error found"
                break
            cmp_mark = forms[i].save(commit = False)            
            if cmp_mark.value > components[i].max_mark or cmp_mark.value < 0:
                error_info = "Invalid mark for %s" % components[i].title
                break;  
            total_mark += cmp_mark.value
            
        if not error_info:             
          
            print total_mark
            # get the student
            student = receiver_form.cleaned_data["student_selection"]   
            print student
            membership = course.member_set.get(person = student)
            print membership
            
            try: 
                ngrade = NumericGrade.objects.get(activity = activity, member = membership)                  
            except NumericGrade.DoesNotExist: #if the corresponding NumericalGrade does not exist yet
                ngrade = NumericGrade(activity = activity, member = membership)                  
                ngrade.save()   
            
            activity_mark = StudentActivityMark(numeric_grade = ngrade)       
            activity_mark.setMark(total_mark)
                                    
            return HttpResponseRedirect(reverse('marking.views.list_activities', \
                                                args=(course_slug,)))       
    else:   
        for i in range(leng):
            forms.append(ActivityComponentMarkForm(prefix = "cmp-form-%s" % (i+1)))       
        receiver_form = MarkReceiverForm(prefix = "receiver-form")
    
    mark_components = []
    for i in range(leng):
        cmp_form = {'component' : components[i], 'form' : forms[i]}        
        mark_components.append(cmp_form)
  
    return render_to_response("marking/marking.html",
                             {'course':course, 'activity' : activity, 'receiver_form' : receiver_form,
                             'mark_components': mark_components, 'error_info': error_info, },\
                             context_instance=RequestContext(request))
    
        