from django.shortcuts import render_to_response, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.core.urlresolvers import reverse
from coredata.models import *
from courselib.auth import *
from grades.models import *
from groups.models import Group
from log.models import *
from models import *      
from forms import *
from django.forms.models import modelformset_factory
from django.contrib import messages
from django.db.models import Q
import decimal


   
# request to views in the marking may comes from different pages, for POST request, we need to redirect to the right page
FROMPAGE = {'course': 'course', 'activityinfo': 'activityinfo', 'activityinfo_group' : 'activityinfo_group'}
def _redirct_response(request, course_slug, activity_slug):   
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


def _find_setup_conflicts(source_setup, target_setup):    
    names_found = set()
    short_names_found = set()
    names_found.update((activity.name for activity in source_setup))
    short_names_found.update((activity.short_name for activity in source_setup))
    conflicting_activities = []
    
    for activity in target_setup:
        if (activity.name in names_found) or (activity.short_name in short_names_found):
                conflicting_activities.append(activity)
    
    return conflicting_activities

def _check_and_save_renamed_activities(all_activities, conflicting_activities, rename_forms, user):
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
            activities_renamed.append({'activity': act, 'old_name': act.name, 'old_short': act.short_name}) 
            act.name = new_name
            act.short_name = new_short_name
            act.slug = None #set to None for regeneration
        else:# this conflicting activity is not to be renamed, add its name and short name to the set 
            act = all_activities.get(id=form.prefix)
            names_found.add(act.name)
            short_names_found.add(act.short_name)             
            
    for act_renamed in activities_renamed:       
        act = act_renamed['activity'] 
        old_name = act_renamed['old_name']
        old_short = act_renamed['old_short']
        act.save()
        #LOG EVENT
        l = LogEntry(userid=user,
              description=("renamed %s(%s) to %s(%s) in course %s") % 
                          (old_name, old_short, act.name, act.short_name, act.offering),
              related_object=act)
        l.save()
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
        target_setup = Activity.objects.filter(offering = course, deleted = False)
        error_info = None        
        source_slug = request.GET.get('copy_from')       
        if source_slug == None: # POST request for selecting the source course to copy from
            select_form = CourseSourceForm(request.POST, prefix = "select-form")
            if select_form.is_valid():
                source_course = select_form.cleaned_data['course'].offering
                source_setup = Activity.objects.filter(offering = source_course, deleted = False) 
                conflicting_acts = _find_setup_conflicts(source_setup, target_setup)
                rename_forms =[ ActivityRenameForm(prefix=act.id) for act in conflicting_acts ]
            else:
                 return render_to_response("marking/select_course_setup.html", 
                             {'course': course, 'select_form': select_form},\
                             context_instance=RequestContext(request))                
            
        else: # POST request for renaming and copy    
            source_course = get_object_or_404(CourseOffering, slug = source_slug)
            source_setup = Activity.objects.filter(offering = source_course, deleted = False)  
            conflicting_acts = _find_setup_conflicts(source_setup, target_setup)   
            
            if conflicting_acts: # check the renamed activities
                rename_forms = [ ActivityRenameForm(request.POST, prefix=act.id) for act in conflicting_acts ]
                error_info = _check_and_save_renamed_activities(
                                   target_setup, conflicting_acts, rename_forms, request.user.username)
            
            if not error_info:# do the copy !
                copyCourseSetup(source_course, course)
                neaten_activity_positions(course)
                #LOG EVENT
                l = LogEntry(userid=request.user.username,
                      description=("copied course setup from %s to %s") % 
                                  (source_course, course),
                      related_object=course)
                l.save()                         
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

def _save_common_problems(formset, activity, user):
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
            if not instance.deleted:
                action = 'saved'
            else:
                action = 'deleted'                                          
            #LOG EVENT#
            l = LogEntry(userid=user,
                  description=("%s common problem %s for %s" % 
                              (action, instance, activity)),
                  related_object=instance)
            l.save()
         
def _save_components(formset, activity, user):
    total_mark = 0
    for form in formset.forms:
        try:  # title is required, empty title triggers KeyError and don't consider this row
            form.cleaned_data['title']
        except KeyError:
            continue
        else:
            instance = form.save(commit = False)
            instance.numeric_activity = activity            
            instance.save()
            
            if not instance.deleted:
                total_mark += instance.max_mark
                action = 'saved'
            else:
                action = 'deleted'                           
            #LOG EVENT#
            l = LogEntry(userid=user,
                  description=("%s marking component %s of %s") % 
                              (action, instance, activity),
                  related_object=instance)  
            l.save()         
            
    return total_mark      

@requires_course_staff_by_slug
def manage_activity_components(request, course_slug, activity_slug):    
           
    error_info = None
    course = get_object_or_404(CourseOffering, slug = course_slug)   
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)   
    fields = ('title', 'description', 'max_mark', 'deleted',)
    
    ComponentsFormSet  = modelformset_factory(ActivityComponent, fields=fields, \
                                              formset=BaseActivityComponentFormSet, \
                                              can_delete = False, extra = 25) 
    
    qset =  ActivityComponent.objects.filter(numeric_activity = activity, deleted=False);
                 
    if request.method == "POST":     
        formset = ComponentsFormSet(activity, request.POST, queryset = qset)
        
        if not formset.is_valid(): 
            if formset.non_form_errors(): # not caused by error of an individual form
                error_info = formset.non_form_errors()[0] 
        else:          
            # save the formset  
            now_max = _save_components(formset, activity, request.user.username)
            messages.add_message(request, messages.SUCCESS, 'Components of %s Saved!' % activity.name)
            # if the max grade changed
            if now_max != activity.max_grade: 
                old_max = activity.max_grade
                activity.max_grade = now_max
                activity.save()               
                messages.add_message(request, messages.WARNING, \
                                     "The max grade of %s updated from %s to %s" % (activity.name, old_max, now_max))
           
            return _redirct_response(request, course_slug, activity_slug)            
    else: # for GET request
        formset = ComponentsFormSet(activity, queryset = qset) 
    
    if error_info:
        messages.add_message(request, messages.ERROR, error_info)
    return render_to_response("marking/components.html", 
                              {'course' : course, 'activity' : activity,\
                               'formset' : formset },\
                               context_instance=RequestContext(request))


@requires_course_staff_by_slug
def import_components(request, course_slug, activity_slug):
    """
    Quick (but not pretty) view to allow importing marking setup from the old system.  Not well tested, but seems to work well enough.
    """
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(NumericalActivity, offering = course, slug = activity_slug)

    if request.method == "POST":
        import json
        from django.db.models import Max, Sum
        form = ImportFileForm(request.POST, request.FILES)
        if form.is_valid():
            max_grade = ActivityComponent.objects.filter(numeric_activity=activity).aggregate(Sum('max_mark'))['max_mark__sum']
            if max_grade is None:
                max_grade = 0

            pos = ActivityComponent.objects.filter(numeric_activity=activity).aggregate(Max('position'))['position__max']
            if pos is None:
                pos = 1
            else:
                pos += 1

            data = request.FILES['file'].read().decode('windows-1252')
            data = json.loads(data)
            for comp in data:
                if len(comp)==0:
                    # ignore the empty object outputted for ease-of-export
                    continue
                ac = ActivityComponent(numeric_activity=activity,
                        max_mark = comp['mark'],
                        title = comp['name'],
                        description = comp['desc'],
                        position = pos)
                ac.save()
                max_grade += comp['mark']
                pos += 1
                for c in comp['common']:
                    if len(c)==0:
                        # ignore the empty object outputted for ease-of-export
                        continue
                    cp = CommonProblem(activity_component=ac,
                            title=c['short'],
                            penalty=str(c['mark']),
                            description=c['long'])
                    cp.save()
            
            # if the max grade changed
            if max_grade != activity.max_grade: 
                old_max = activity.max_grade
                activity.max_grade = max_grade
                activity.save()               
                messages.add_message(request, messages.WARNING, \
                                     "The max grade of %s updated from %s to %s" % (activity.name, old_max, max_grade))
            #LOG EVENT
            l = LogEntry(userid=request.user.username,
                  description=("imported marking setup for %s") % (activity),
                  related_object=activity)
            l.save()                         
            messages.add_message(request, messages.SUCCESS, "Marking setup imported.")                
            return HttpResponseRedirect(reverse('marking.views.manage_activity_components', kwargs={'course_slug':course_slug, 'activity_slug': activity_slug}))
    else:
        form = ImportFileForm()
    return render_to_response("marking/import.html", 
                              {'course': course, 'activity': activity, 'form': form},\
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
            _save_common_problems(formset, activity, request.user.username)
            messages.add_message(request, messages.SUCCESS, 'Common problems Saved')
            return HttpResponseRedirect(reverse('marking.views.manage_common_problems', kwargs={'course_slug': activity.offering.slug, 'activity_slug': activity.slug}))
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
            
           #LOG EVENT
            l = LogEntry(userid=request.user.username,
                  description=("updated positions of marking components in %s") % activity,
                  related_object=activity)
            l.save()        
                
            return HttpResponse("Positions of components updated !")
           
    return render_to_response("marking/component_positions.html",
                              {'course' : course, 'activity' : activity,\
                               'components': components, 'components': components},\
                               context_instance=RequestContext(request))
    
    
def XXX_initialize_component_mark_forms(components, base_activity_mark=None):
    
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

def XXX_construct_mark_components(components, component_mark_forms):
    assert len(components)==len(component_mark_forms)
    mark_components = []
    for i in range(len(components)):
        # select common problems belong to each component
        common_problems = CommonProblem.objects.filter(activity_component = components[i], deleted = False)
        comp = {'component' : components[i], 'form' : component_mark_forms[i], 'common_problems' : common_problems}        
        mark_components.append(comp)
    
    return mark_components              
    
def XXX_check_component_marks_forms(components, component_mark_forms, warnings_to_return):
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

def XXX_check_additional_info_form(addtional_info_form, warnings_to_return):
    """ 
    Return the ActivityMark object containing additional information
    if error found return None
    """
    if addtional_info_form.is_valid():        
        return addtional_info_form.save(commit = False)   
    return None

def XXX_compute_final_mark(component_marks, max_grade, additional_info):
    components_total = 0
    for cmp_mark in component_marks:   
        components_total += cmp_mark.value
   
    return  (1-additional_info.late_penalty/decimal.Decimal(100))*components_total - \
            additional_info.mark_adjustment

def XXX_save_marking_results(activity, activity_mark, final_mark, marker_ident, mark_receiver_ident, component_marks = None, additional_info=None):
    
    # copy the additional info      
    if additional_info != None:
        activity_mark.copyFrom(additional_info)
    activity_mark.setMark(final_mark)           
    activity_mark.created_by = marker_ident
    activity_mark.activity = activity
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
      
@requires_course_staff_by_slug      
def change_grade_status(request, course_slug, activity_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(NumericActivity, offering=course, slug=activity_slug)
    member = get_object_or_404(Member, offering=course, person__userid = userid, role = 'STUD')
    grades = NumericGrade.objects.filter(activity=activity, member=member)
    if grades:
        numeric_grade = grades[0]
    else:
        numeric_grade = NumericGrade(activity=activity, member=member, flag="GRAD")
    
    if 'status' in request.GET:
        numeric_grade.flag = request.GET['status']
    error = None
    if request.method == 'POST':
        status_form = GradeStatusForm(data=request.POST, instance=numeric_grade, prefix='grade-status')
        if not status_form.is_valid(): 
            error = 'Error found'
        else:            
            status_form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("changed the grade of student %s to %s (%s) on %s.  Comment: '%s'") % 
                              (userid, numeric_grade.value, FLAGS[numeric_grade.flag], activity, numeric_grade.comment),
                  related_object=numeric_grade)
            l.save()
                
            messages.add_message(request, messages.SUCCESS, 
               'Grade status for student %s on %s changed!' % (userid, activity.name,))                           
            return _redirct_response(request, course_slug, activity_slug)        
    else:
        status_form = GradeStatusForm(instance=numeric_grade, prefix='grade-status')
        
    if error:        
        messages.add_message(request, messages.ERROR, error)    
    context = {'course':course,'activity' : activity,\
               'student' : member.person, 'current_status' : FLAGS[numeric_grade.flag],
               'status_form': status_form}
    return render_to_response("marking/grade_status.html", context,
                              context_instance=RequestContext(request))  

def _marking_view(request, course_slug, activity_slug, userid, groupmark=False):
    """
    Function to handle all of the marking views (individual/group, new/editing, GET/POST).
    
    Long and has lots of conditional code, but avoids logic duplication.
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)    
    activity = get_object_or_404(NumericActivity, offering=course, slug=activity_slug)     
    components = ActivityComponent.objects.filter(numeric_activity=activity, deleted=False)
    if groupmark:
        group = get_object_or_404(Group, slug=userid)
        ActivityMarkForm = GroupActivityMarkForm
    else:
        student = get_object_or_404(Person, userid=userid)
        membership = get_object_or_404(Member, offering=course, person=student, role='STUD') 
        ActivityMarkForm = StudentActivityMarkForm
    
    # set up forms (all cases handled here to avoid duplicating the logic)
    postdata = None
    filedata = None
    am = None
    if request.method == 'POST':
        # use POST data when creating forms
        postdata = request.POST
        filedata = request.FILES
    elif 'base_activity_mark' in request.GET:
        # requested "mark based on": get that object
        old_id = request.GET['base_activity_mark']
        if groupmark:
            am = get_group_mark_by_id(activity, group, old_id)
        else:
            am = get_activity_mark_by_id(activity, membership, old_id)
    elif 'load_old' in request.GET:
        # requested load any previous mark: get that object
        try:
            if groupmark:
                am = get_group_mark(activity, group)
            else:
                am = get_activity_mark_for_student(activity, membership)
        except NumericGrade.DoesNotExist:
            pass

        if am:
            messages.add_message(request, messages.INFO, 'There was a previous mark for this student.  Details are below.')
        

    # build forms
    form = ActivityMarkForm(instance=am, data=postdata, files=filedata)
    component_data = []
    for i,c in enumerate(components):
        old_c = None
        if am:
            try:
                old_c = am.activitycomponentmark_set.filter(activity_component=c)[0]
            except IndexError: # just in case: leave old_c==None if old one can't be found in database
                pass
        f = ActivityComponentMarkForm(instance=old_c, data=postdata, prefix="cmp-%s" % (i+1))
        common = CommonProblem.objects.filter(activity_component=c, deleted=False)
        component_data.append( {'component': c, 'form': f, 'common_problems': common } )
    
    # handle POST for writing mark
    if request.method == 'POST':
        # base form *and* all components must be valid to continue
        if form.is_valid() and (False not in [entry['form'].is_valid() for entry in component_data]):
            # set additional ActivityMark info
            am = form.save(commit=False)
            am.created_by = request.user.username
            am.activity = activity
            if 'file_attachment' in request.FILES:
                # also store MIME type for uploaded file
                upfile = request.FILES['file_attachment']
                filetype = upfile.content_type
                if upfile.charset:
                    filetype += "; charset=" + upfile.charset
                am.file_mediatype = filetype

            if groupmark:
                # set group info
                am.group = group
                am.numeric_activity = activity
            else:
                # need a corresponding NumericGrade object: find or create one
                try:       
                    ngrade = NumericGrade.objects.get(activity=activity, member=membership)
                except NumericGrade.DoesNotExist:
                    ngrade = NumericGrade(activity=activity, member=membership)
                    ngrade.save(newsitem=False)
                am.numeric_grade = ngrade
            
            # calculate grade and save
            total = decimal.Decimal(0)
            for entry in component_data:
                value = entry['form'].cleaned_data['value']
                total += value
                if value > entry['component'].max_mark:
                    messages.add_message(request, messages.WARNING, "Bonus marks given for %s" % (entry['component'].title))
                if value < 0:
                    messages.add_message(request, messages.WARNING, "Negative mark given for %s" % (entry['component'].title))
            
            mark = (1-form.cleaned_data['late_penalty']/decimal.Decimal(100)) * \
                   (total - form.cleaned_data['mark_adjustment'])
            am.setMark(mark)

            am.save()
            form.save_m2m()
            for entry in component_data:
                c = entry['form'].save(commit=False)
                c.activity_component = entry['component']
                c.activity_mark = am
                c.save()
                entry['form'].save_m2m()

            if groupmark:
                messages.add_message(request, messages.SUCCESS, 'Mark for group "%s" on %s saved: %s/%s.' % (group.name, activity.name, mark, activity.max_grade))
            else:
                messages.add_message(request, messages.SUCCESS, 'Mark for %s on %s saved: %s/%s.' % (student.name(), activity.name, mark, activity.max_grade))
            #LOG EVENT
            l = LogEntry(userid=request.user.username,
                  description=("marked %s for %s: %s/%s") % (activity, userid, mark, activity.max_grade),
                  related_object=am)
            l.save()

            # redirect to next page
            if 'marknext' in request.POST:
                # "submit and mark next" clicked: jump to next userid
                try:
                    nextmember = Member.objects.filter(offering=course, person__userid__gt=userid, role="STUD"
                                 ).order_by('person__userid')[0]
                    return HttpResponseRedirect(reverse(marking_student, 
                           kwargs={'course_slug': course.slug, 'activity_slug': activity.slug,
                           'userid': nextmember.person.userid}) + "?load_old")
                except IndexError:
                    messages.add_message(request, messages.INFO, 'That was the last userid in the course.')
            elif groupmark:
                return HttpResponseRedirect(reverse('grades.views.activity_info_with_groups', 
                           kwargs={'course_slug': course.slug, 'activity_slug': activity.slug}))

            return _redirct_response(request, course_slug, activity_slug)

    # display form for GET or failed validation
    context = {'course': course, 'activity': activity, 'form': form, 'component_data': component_data }
    if groupmark:
        context['group'] = group
    else:
        context['student'] = student
    return render_to_response("marking/marking.html", context, context_instance=RequestContext(request))  
    

@requires_course_staff_by_slug
def marking_student(request, course_slug, activity_slug, userid):
    return _marking_view(request, course_slug, activity_slug, userid, groupmark=False)

@requires_course_staff_by_slug
def marking_group(request, course_slug, activity_slug, group_slug):
    return _marking_view(request, course_slug, activity_slug, group_slug, groupmark=True)

@requires_course_staff_by_slug
def XXX_marking_student(request, course_slug, activity_slug, userid):
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

            messages.add_message(request, messages.SUCCESS, 'Mark for student %s on %s saved!' % (userid, activity.name,))
            for warning in warning_messages:
                messages.add_message(request, messages.WARNING, warning)                      
            if 'marknext' in request.POST:
                # "submit and mark next" clicked: jump to next userid
                try:
                    nextmember = Member.objects.filter(offering=course, person__userid__gt=userid, role="STUD"
                                 ).order_by('person__userid')[0]
                    return HttpResponseRedirect(reverse(marking_student, 
                           kwargs={'course_slug': course.slug, 'activity_slug': activity.slug,
                           'userid': nextmember.person.userid}))
                except IndexError:
                    messages.add_message(request, messages.WARNING, 'That was the last userid in the course.')
                    return _redirct_response(request, course_slug, activity_slug)
            else:
                return _redirct_response(request, course_slug, activity_slug)
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
def XXX_marking_group(request, course_slug, activity_slug, group_slug):    
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
            return _redirct_response(request, course_slug, activity_slug)
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
     course = get_object_or_404(CourseOffering, slug = course_slug)    
     activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)     

     if is_course_staff_by_slug(request.user, course_slug):
         is_staff = True
     elif is_course_student_by_slug(request.user, course_slug):
         if userid != request.user.username or activity.status != "RLS":
             return ForbiddenResponse(request)
         is_staff = False
     else:
         return ForbiddenResponse(request)
    
     student = get_object_or_404(Person, userid = userid)
     membership = get_object_or_404(Member,offering = course, person = student, role = 'STUD')
          
     act_mark_id = request.GET.get('activity_mark')
     if act_mark_id != None: # if act_mark_id specified in the url
         act_mark = get_activity_mark_by_id(activity, membership, act_mark_id) 
     else:
         act_mark = get_activity_mark_for_student(activity, membership)
     
     if act_mark == None:
         return render_to_response("marking/mark_summary_none.html", 
                               {'course':course, 'activity' : activity, 'student' : student, \
                                'is_staff': is_staff}, \
                                context_instance = RequestContext(request))
    
     group = None
     if hasattr(act_mark, 'group'):
        group = act_mark.group
                      
     component_marks = ActivityComponentMark.objects.filter(activity_mark = act_mark)      
    
     return render_to_response("marking/mark_summary.html", 
                               {'course':course, 'activity' : activity, 'student' : student, 'group' : group, \
                                'activity_mark': act_mark, 'component_marks': component_marks, \
                                'is_staff': is_staff, 'view_history': act_mark_id == None}, \
                                context_instance = RequestContext(request))

@login_required
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
         
import os
@login_required
def download_marking_attachment(request, course_slug, activity_slug, mark_id):
    course = get_object_or_404(CourseOffering, slug=course_slug)    
    activity = get_object_or_404(NumericActivity, offering=course, slug=activity_slug)

    if is_course_staff_by_slug(request.user, course_slug):
       is_staff = True
    elif is_course_student_by_slug(request.user, course_slug):
       is_staff = False
    else:
       return ForbiddenResponse(request)

    # get the ActivityMark object
    try:
        am = StudentActivityMark.objects.get(id=mark_id)
        groupmark = False
    except StudentActivityMark.DoesNotExist:
        try:
            am = GroupActivityMark.objects.get(id=mark_id)
            groupmark = True
        except GroupActivityMark.DoesNotExist:
            return NotFoundResponse(request)
    
    # check permissions:
    if is_staff:
        pass
    elif groupmark:
        # must be member of the group for this activity
        gms = am.group.groupmember_set.filter(student__person__userid=request.user.username, activity=activity, confirmed=True)
        if not gms:
            return ForbiddenResponse(request)
    else:
        # must be corresponding student
        if am.numeric_grade.member.userid != request.user.username:
            return ForbiddenResponse(request)
    
    # send the file
    filename = am.attachment_filename()
    response = HttpResponse(am.file_attachment, mimetype=am.file_mediatype)
    response['Content-Disposition'] = 'inline; filename='+filename
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
from grades.models import FLAG_CHOICES
@requires_course_staff_by_slug
def export_csv(request, course_slug, activity_slug):    
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)   
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s_%s.csv' % (course_slug, activity_slug,)

    writer = csv.writer(response)
    if activity.group:
        writer.writerow(['Student ID', 'User ID', 'Student Name', 'Grade', 'Group', 'Group ID'])
        gms = GroupMember.objects.filter(activity=activity).select_related('student__person', 'group')
        gms = dict((gm.student.person.userid, gm) for gm in gms)
    else:
        writer.writerow(['Student ID', 'User ID', 'Student Name', 'Grade'])
    
    student_members = Member.objects.filter(offering = course, role = 'STUD').select_related('person')
    for std in student_members:
        row = [std.person.emplid, std.person.userid, std.person.name()]
        try: 
            ngrade = NumericGrade.objects.get(activity = activity, member = std)                  
        except NumericGrade.DoesNotExist: #if the NumericGrade does not exist yet,
            row.append('no grade')
        else:
            if ngrade.flag == 'GRAD' or ngrade.flag == 'CALC':
                row.append(ngrade.value)
            elif ngrade.flag == 'NOGR':
                row.append('no grade')
            else:
                row.append(ngrade.flag)
        
        if activity.group:
            if std.person.userid in gms:
                row.append(gms[std.person.userid].group.name)
                row.append(gms[std.person.userid].group.slug)
            else:
                row.append('')
                row.append('')

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
            i = -1
            for group in groups:
               i += 1
               new_value = rows[i]['form'].cleaned_data['value']
               if new_value== None :
                   continue
               if current_act_marks[i] != None and current_act_marks[i].mark == new_value:
                  # if any of the group members originally has a grade status other than 'GRAD'
                  # so do not override the status
                  continue
               act_mark = GroupActivityMark(group=group, numeric_activity=activity, created_by=request.user.username)
               act_mark.setMark(new_value)
               act_mark.save()

               updated += 1     
               if new_value < 0:
                   warning_info.append("Negative mark given to group %s" % group.name)
               elif new_value > activity.max_grade:
                   warning_info.append("Bonus mark given to group %s" % group.name)  

               #LOG EVENT
               l = LogEntry(userid=request.user.username,
                     description=("bulk marked %s for group '%s': %s/%s") % (activity, group.name, new_value, activity.max_grade),
                     related_object=act_mark)
               l.save()                  
                 
            if updated > 0:
                messages.add_message(request, messages.SUCCESS, "Marks for all groups on %s saved (%s groups' grades updated)!" % (activity.name, updated))
            for warning in warning_info:
                messages.add_message(request, messages.WARNING, warning)                    
            return _redirct_response(request, course_slug, activity_slug)   
        
    else: # for GET request
       for group in groups: 
           act_mark = get_group_mark(activity, group)         
           if act_mark == None:
                current_mark = 'no grade'
           else:
                current_mark = act_mark.mark
           entry_form = MarkEntryForm(prefix = group.name)                                    
           rows.append({'group': group, 'current_mark' : current_mark, 'form' : entry_form}) 
    
    if error_info:
        messages.add_message(request, messages.ERROR, error_info)     
    return render_to_response("marking/mark_all_group.html",
                          {'course': course, 'activity': activity,'mark_all_rows': rows }, 
                          context_instance = RequestContext(request))


            
######################### Henry Added #############################
# This is for marking groups with letter grades
@requires_course_staff_by_slug
def mark_all_groups_lettergrade (request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(LetterActivity, offering=course, slug=activity_slug)
    rows = [] 
    
    return render_to_response("marking/mark_all_group_lettergrade.html",
                          {'course': course, 'activity': activity,'mark_all_rows': rows }, 
                          context_instance = RequestContext(request))


#This is for marking students with letter grades
@requires_course_staff_by_slug
def mark_all_students_lettergrade(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(LetterActivity, offering = course, slug = activity_slug)
    fileform = None
    rows = []  
    
    return render_to_response("marking/mark_all_student_lettergrade.html",{'course': course, 'activity': activity,\
                              'fileform' : fileform,'too_many': len(rows) >= 100,\
                              'mark_all_rows': rows }, context_instance = RequestContext(request))            
#This is for change grade status of letter grades
@requires_course_staff_by_slug      
def change_grade_status_lettergrade(request, course_slug, activity_slug, userid):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(LetterActivity, offering=course, slug=activity_slug)
    member = get_object_or_404(Member, offering=course, person__userid = userid, role = 'STUD')
    grades = LetterGrade.objects.filter(activity=activity, member=member)
    if grades:
        letter_grade = grades[0]
    else:
        letter_grade = LetterGrade(activity=activity, member=member, flag="GRAD")
    
    if 'status' in request.GET:
        letter_grade.flag = request.GET['status']
    error = None
    if request.method == 'POST':
        status_form = GradeStatusForm_LetterGrade(data=request.POST, instance=letter_grade, prefix='grade-status')
        if not status_form.is_valid(): 
            error = 'Error found'
        else:            
            status_form.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("changed the grade of student %s to %s (%s) on %s.  Comment: '%s'") % 
                              (userid, letter_grade.letter_grade, FLAGS[letter_grade.flag], activity, letter_grade.comment),
                  related_object=letter_grade)
            l.save()
                
            messages.add_message(request, messages.SUCCESS, 
               'Grade status for student %s on %s changed!' % (userid, activity.name,))                           
            return _redirct_response(request, course_slug, activity_slug)        
    else:
        status_form = GradeStatusForm_LetterGrade(instance=letter_grade, prefix='grade-status')
        
    if error:        
        messages.add_message(request, messages.ERROR, error)    
    context = {'course':course,'activity' : activity,\
               'student' : member.person, 'current_status' : FLAGS[letter_grade.flag],
               'status_form': status_form}
    return render_to_response("marking/grade_status_lettergrade.html", context,
                              context_instance=RequestContext(request))  

######################### Henry Added #############################    

@requires_course_staff_by_slug
def mark_all_students(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug)
   
    rows = []
    fileform = None
    imported_data = {} #may get filled with data from an imported file, a mapping from student's userid to grade
    error_info = None 
    warning_info = []
    memberships = Member.objects.select_related('person').filter(offering = course, role = 'STUD')    
    
    if request.method == 'POST' and request.GET.get('import') != 'true':
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
            rows.append({'student': student, 'current_grade' : current_grade, 'form' : entry_form})    
       
        # save if needed 
        if error_info == None:
            updated = 0                 
            for i in range(len(memberships)):
               student = memberships[i].person  
               ngrade = ngrades[i]
               new_value = rows[i]['form'].cleaned_data['value'] 
               # the new mark is blank or the new mark is the same as the old one, do nothing
               if new_value == None: 
                   continue
               if ngrade !=None and ngrade.value == new_value:
                   # if the student originally has a grade status other than 'GRAD',
                   # we do not override that status
                   continue 
               # save data 
               if ngrade == None:
                    ngrade = NumericGrade(activity = activity, member = memberships[i]);
               ngrade.value = new_value
               ngrade.flag = "GRAD"
               ngrade.save()
               
               updated += 1     
               if new_value < 0:
                   warning_info.append("Negative mark given to %s on %s" %(student.userid, activity.name))
               elif new_value > activity.max_grade:
                   warning_info.append("Bonus mark given to %s on %s" %(student.userid, activity.name))
               
               #LOG EVENT
               l = LogEntry(userid=request.user.username,
                     description=("bulk marked %s for %s: %s/%s") % (activity, student.userid, new_value, activity.max_grade),
                     related_object=ngrade)
               l.save()                  
           
            if updated > 0:
                messages.add_message(request, messages.SUCCESS, "Marks for all students on %s saved (%s students' grades updated)!" % (activity.name, updated))
                for warning in warning_info:
                    messages.add_message(request, messages.WARNING, warning)
                    
            return _redirct_response(request, course_slug, activity_slug) 
    
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


            
        
