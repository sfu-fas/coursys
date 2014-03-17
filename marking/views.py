import io
import unicodecsv as csv
import json
import decimal

from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.forms.models import ModelChoiceField, modelformset_factory
from django.forms.forms import Form
from django.db.models import Q, Max, Sum
from django.db import transaction
from django.shortcuts import render_to_response, render, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from models import ActivityComponent, CommonProblem, ActivityComponentMark
from models import GroupActivityMark, GroupActivityMark_LetterGrade, StudentActivityMark
from models import get_activity_mark_by_id, get_activity_mark_for_student, get_group_mark_by_id, get_group_mark
from models import copyCourseSetup, neaten_activity_positions
from coredata.models import Person, CourseOffering, Member
from grades.models import FLAGS, Activity, NumericActivity, NumericGrade
from grades.models import LetterActivity, LetterGrade, LETTER_GRADE_CHOICES_IN, get_entry_person
from log.models import LogEntry
from groups.models import Group, GroupMember, all_activities_filter

from courselib.auth import requires_course_staff_by_slug, is_course_staff_by_slug, is_course_student_by_slug,\
    ForbiddenResponse, NotFoundResponse
from featureflags.flags import uses_feature

from marking.forms import BaseCommonProblemFormSet, BaseActivityComponentFormSet
from marking.forms import ActivityRenameForm
from marking.forms import ImportFileForm, ImportMarkFileForm
from marking.forms import GradeStatusForm, GradeStatusForm_LetterGrade
from marking.forms import ActivityMarkForm, GroupActivityMarkForm, StudentActivityMarkForm, ActivityComponentMarkForm
from marking.forms import MarkEntryForm, MarkEntryForm_LetterGrade
from marking.forms import UploadGradeFileForm, UploadGradeFileForm_LetterGrade

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
              description=(u"renamed %s(%s) to %s(%s) in course %s") % 
                          (old_name, old_short, act.name, act.short_name, act.offering),
              related_object=act)
        l.save()
    return None


@uses_feature('marking')
@requires_course_staff_by_slug
@transaction.atomic
def copy_course_setup(request, course_slug):
    userid = request.user.username  
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    # get the course offerings of this user except for this course
    courses_qset = Member.objects.exclude(role__in=["DROP","STUD"]).exclude(offering=course) \
            .filter(offering__graded=True, person__userid=userid) \
            .select_related('offering','offering__semester')
   
    from pages.models import Page
    class CourseChoiceField(ModelChoiceField):
        def label_from_instance(self, obj):
            return "%s" % (obj.offering)
    class CourseSourceForm(Form):
        course = CourseChoiceField(label="Source course", queryset=courses_qset)
    
    if request.method == "POST":         
        target_setup = Activity.objects.filter(offering = course, deleted = False)
        error_info = None        
        source_slug = request.GET.get('copy_from')       
        if source_slug == None: # POST request for selecting the source course to copy from
            select_form = CourseSourceForm(request.POST, prefix = "select-form")
            if select_form.is_valid():
                source_course = select_form.cleaned_data['course'].offering
                source_setup = Activity.objects.filter(offering = source_course, deleted = False)
                source_pages = Page.objects.filter(offering=source_course)
                conflicting_acts = _find_setup_conflicts(source_setup, target_setup)
                rename_forms =[ ActivityRenameForm(prefix=act.id) for act in conflicting_acts ]
            else:
                return render_to_response("marking/select_course_setup.html", 
                             {'course': course, 'select_form': select_form},\
                             context_instance=RequestContext(request))                
            
        else: # POST request for renaming and copy    
            source_course = get_object_or_404(CourseOffering, slug = source_slug)
            source_setup = Activity.objects.filter(offering = source_course, deleted = False) 
            source_pages = Page.objects.filter(offering=source_course)
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
                      description=(u"copied course setup from %s to %s") % 
                                  (source_course, course),
                      related_object=course)
                l.save()                         
                messages.add_message(request, messages.SUCCESS, \
                        "Course Setup copied from %s (%s)" % (source_course.name(), source_course.semester.label(),))                
                return HttpResponseRedirect(reverse('grades.views.course_info', args=(course_slug,)))
        
        if error_info:
            messages.add_message(request, messages.ERROR, error_info)   
        
        return render(request, "marking/copy_course_setup.html",\
                {'course' : course, 'source_course' : source_course, "source_pages": source_pages,\
                'source_setup' : source_setup, 'conflicting_activities' : zip(conflicting_acts, rename_forms)})
            
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
                  description=(u"%s common problem %s for %s" % 
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
                  description=(u"%s marking component %s of %s") % 
                              (action, instance, activity),
                  related_object=instance)  
            l.save()         
            
    return total_mark      

@requires_course_staff_by_slug
@transaction.atomic
def manage_activity_components(request, course_slug, activity_slug):    
    error_info = None
    course = get_object_or_404(CourseOffering, slug = course_slug)   
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug, deleted=False)   
    fields = ('title', 'description', 'max_mark', 'deleted',)
    ComponentsFormSet  = modelformset_factory(ActivityComponent, fields=fields, \
                                              formset=BaseActivityComponentFormSet, \
                                              can_delete = False, extra = 25) 
    
    qset = ActivityComponent.objects.filter(numeric_activity = activity, deleted=False)
                 
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
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug, deleted=False)

    if request.method == "POST":
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
                  description=(u"imported marking setup for %s") % (activity),
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
@transaction.atomic
@uses_feature('marking')
def manage_common_problems(request, course_slug, activity_slug):    
       
    error_info = None
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug, deleted=False) 
   
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
@transaction.atomic
@uses_feature('marking')
def manage_component_positions(request, course_slug, activity_slug): 
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug, deleted=False)
    components =  ActivityComponent.objects.filter(numeric_activity = activity, deleted=False); 
    
    if request.method == 'POST':
        if request.is_ajax():
            component_ids = request.POST.getlist('ids[]') 
            position = 1;
            for cid in component_ids:
                comp = get_object_or_404(components, id=cid)
                comp.position = position
                comp.save()
                position += 1
            
            #LOG EVENT
            l = LogEntry(userid=request.user.username,
                  description=(u"updated positions of marking components in %s") % activity,
                  related_object=activity)
            l.save()        
                
            return HttpResponse("Positions of components updated !")
           
    return render_to_response("marking/component_positions.html",
                              {'course' : course, 'activity' : activity,\
                               'components': components, 'components': components},\
                               context_instance=RequestContext(request))
    


@requires_course_staff_by_slug
@uses_feature('marking')
def change_grade_status(request, course_slug, activity_slug, userid):
    """
    Grade status form.  Calls numeric/letter view as appropriate.
    """
    course = get_object_or_404(CourseOffering, slug = course_slug)
    acts = all_activities_filter(course, slug=activity_slug)
    if len(acts) != 1:
        raise Http404('No such Activity.')
    activity = acts[0]
    
    if isinstance(activity, NumericActivity):
        return _change_grade_status_numeric(request, course, activity, userid)
    elif isinstance(activity, LetterActivity):
        return _change_grade_status_letter(request, course, activity, userid)
    else:
        raise Http404('Unknown activity type.')


@transaction.atomic
def _change_grade_status_numeric(request, course, activity, userid):
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
            status_form.save(commit=False)
            numeric_grade.save(entered_by=request.user.username)

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=(u"changed the grade of student %s to %s (%s) on %s.  Comment: '%s'") % 
                              (userid, numeric_grade.value, FLAGS[numeric_grade.flag], activity, numeric_grade.comment),
                  related_object=numeric_grade)
            l.save()
                
            messages.add_message(request, messages.SUCCESS, 
               'Grade status for student %s on %s changed!' % (userid, activity.name,))                           
            return _redirct_response(request, course.slug, activity.slug)        
    else:
        status_form = GradeStatusForm(instance=numeric_grade, prefix='grade-status')
        
    if error:        
        messages.add_message(request, messages.ERROR, error)    
    context = {'course':course,'activity' : activity,\
               'student' : member.person, 'current_status' : FLAGS[numeric_grade.flag],
               'status_form': status_form}
    return render_to_response("marking/grade_status.html", context,
                              context_instance=RequestContext(request))  

@transaction.atomic
def _change_grade_status_letter(request, course, activity, userid):
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
            status_form.save(commit=False)
            letter_grade.save(entered_by=request.user.username)

            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=(u"changed the grade of student %s to %s (%s) on %s.  Comment: '%s'") % 
                              (userid, letter_grade.letter_grade, FLAGS[letter_grade.flag], activity, letter_grade.comment),
                  related_object=letter_grade)
            l.save()
                
            messages.add_message(request, messages.SUCCESS, 
               'Grade status for student %s on %s changed!' % (userid, activity.name,))                           
            return _redirct_response(request, course.slug, activity.slug)        
    else:
        status_form = GradeStatusForm_LetterGrade(instance=letter_grade, prefix='grade-status')
        
    if error:        
        messages.add_message(request, messages.ERROR, error)    
    context = {'course':course,'activity' : activity,\
               'student' : member.person, 'current_status' : FLAGS[letter_grade.flag],
               'status_form': status_form}
    return render_to_response("marking/grade_status_lettergrade.html", context,
                              context_instance=RequestContext(request))  


@transaction.atomic
@uses_feature('marking')
def _marking_view(request, course_slug, activity_slug, userid, groupmark=False):
    """
    Function to handle all of the marking views (individual/group, new/editing, GET/POST).
    
    Long and has lots of conditional code, but avoids logic duplication.
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)    
    activity = get_object_or_404(NumericActivity, offering=course, slug=activity_slug, deleted=False)     
    components = ActivityComponent.objects.filter(numeric_activity=activity, deleted=False)
    if groupmark:
        group = get_object_or_404(Group, slug=userid, courseoffering=course)
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
        try:
            old_id = int(old_id)
        except ValueError:
            am = None
        else:
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
        f = ActivityComponentMarkForm(component=c, instance=old_c, data=postdata, prefix="cmp-%s" % (i+1))
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
                    ngrade.save(newsitem=False, entered_by=None, is_temporary=True)
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

            am.setMark(mark, entered_by=request.user.username)
            am.save()
            form.save_m2m()
            for entry in component_data:
                c = entry['form'].save(commit=False)
                c.activity_component = entry['component']
                c.activity_mark = am
                c.save()
                entry['form'].save_m2m()

            if groupmark:
                messages.add_message(request, messages.SUCCESS, u'Mark for group "%s" on %s saved: %s/%s.' % (group.name, activity.name, mark, activity.max_grade))
            else:
                messages.add_message(request, messages.SUCCESS, u'Mark for %s on %s saved: %s/%s.' % (student.name(), activity.name, mark, activity.max_grade))
            #LOG EVENT
            l = LogEntry(userid=request.user.username,
                  description=(u"marked %s for %s: %s/%s") % (activity, userid, mark, activity.max_grade),
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
@uses_feature('marking')
def marking_student(request, course_slug, activity_slug, userid):
    return _marking_view(request, course_slug, activity_slug, userid, groupmark=False)

@requires_course_staff_by_slug
@uses_feature('marking')
def marking_group(request, course_slug, activity_slug, group_slug):
    return _marking_view(request, course_slug, activity_slug, group_slug, groupmark=True)



@login_required
def mark_summary_student(request, course_slug, activity_slug, userid):
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug, deleted=False)     

    if is_course_staff_by_slug(request, course_slug):
        is_staff = True
    elif is_course_student_by_slug(request, course_slug):
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
    if is_course_staff_by_slug(request, course_slug):
        is_staff = True
    elif is_course_student_by_slug(request, course_slug):
        is_staff = False
    else:
        return ForbiddenResponse(request)
    
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug, deleted=False)    
    group = get_object_or_404(Group, courseoffering = course, slug = group_slug)
     
    if not is_staff:
        gm = GroupMember.objects.filter(group=group, student__person__userid=request.user.userid)
        if not gm:
            return ForbiddenResponse(request)
     
    act_mark_id = request.GET.get('activity_mark')
    if act_mark_id != None: 
        act_mark = get_group_mark_by_id(activity, group, act_mark_id)
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
         
@login_required
def download_marking_attachment(request, course_slug, activity_slug, mark_id):
    course = get_object_or_404(CourseOffering, slug=course_slug)    
    activity = get_object_or_404(NumericActivity, offering=course, slug=activity_slug, deleted=False)

    if is_course_staff_by_slug(request, course_slug):
        is_staff = True
    elif is_course_student_by_slug(request, course_slug):
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
        if am.numeric_grade.member.person.userid != request.user.username:
            return ForbiddenResponse(request)
    
    # send the file
    filename = am.attachment_filename()
    response = HttpResponse(am.file_attachment, content_type=am.file_mediatype)
    response['Content-Disposition'] = 'inline; filename="' + filename + '"'
    return response

@requires_course_staff_by_slug
def mark_history_student(request, course_slug, activity_slug, userid):
    """
    show the marking history for the student on the activity
    """
    student = get_object_or_404(Person, userid=userid)
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug, deleted=False)     
    membership = get_object_or_404(Member, offering = course, person = student, role = 'STUD') 
    
    context = {'course': course, 'activity' : activity, 'student' : student,}
    mark_history_info = get_activity_mark_for_student(activity, membership, True)
    if not mark_history_info:
        return NotFoundResponse(request)
    context.update(mark_history_info)
    return render_to_response("marking/mark_history_student.html", context, context_instance = RequestContext(request))

@requires_course_staff_by_slug
def mark_history_group(request, course_slug, activity_slug, group_slug):
    """
    show the marking history for the group on the activity
    """
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(NumericActivity, offering = course, slug = activity_slug, deleted=False)     
    group = get_object_or_404(Group, courseoffering = course, slug = group_slug) 
    
    context = {'course': course, 'activity' : activity, 'group' : group,}
    mark_history_info = get_group_mark(activity, group, True)
    context.update(mark_history_info)    
    return render_to_response("marking/mark_history_group.html", context, context_instance = RequestContext(request))
    

@requires_course_staff_by_slug
def export_csv(request, course_slug, activity_slug):
    """
    Export grades in CSV.  Calls numeric/letter view as appropriate.
    """
    course = get_object_or_404(CourseOffering, slug = course_slug)
    acts = all_activities_filter(course, slug=activity_slug)
    if len(acts) != 1:
        raise Http404('No such Activity.')
    activity = acts[0]
    
    if isinstance(activity, NumericActivity):
        return _export_csv_numeric(request, course, activity)
    elif isinstance(activity, LetterActivity):
        return _export_csv_letter(request, course, activity)
    else:
        raise Http404('Unknown activity type.')


def _export_csv_numeric(request, course, activity):    
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s_%s.csv"' % (course.slug, activity.slug,)

    writer = csv.writer(response)
    if activity.group:
        writer.writerow([Person.emplid_header(), Person.userid_header(), 'Student Name', activity.short_name, 'Group', 'Group ID'])
        gms = GroupMember.objects.filter(activity=activity).select_related('student__person', 'group')
        gms = dict((gm.student.person.userid, gm) for gm in gms)
    else:
        writer.writerow([Person.emplid_header(), Person.userid_header(), 'Student Name', activity.short_name])
    
    student_members = Member.objects.filter(offering = course, role = 'STUD').select_related('person')
    for std in student_members:
        row = [std.person.emplid, std.person.userid, std.person.name()]
        try: 
            ngrade = NumericGrade.objects.get(activity = activity, member = std)                  
        except NumericGrade.DoesNotExist: #if the NumericGrade does not exist yet,
            row.append('')
        else:
            if ngrade.flag == 'GRAD' or ngrade.flag == 'CALC':
                row.append(ngrade.value)
            elif ngrade.flag == 'NOGR':
                row.append('')
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


def _export_csv_letter(request, course, activity):
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s_%s.csv"' % (course.slug, activity.slug,)

    writer = csv.writer(response)
    
    if activity.group:
        writer.writerow([Person.emplid_header(), Person.userid_header(), 'Student Name', activity.short_name, 'Group', 'Group ID'])
        gms = GroupMember.objects.filter(activity=activity).select_related('student__person', 'group')
        gms = dict((gm.student.person.userid, gm) for gm in gms)
    else:
        writer.writerow([Person.emplid_header(), Person.userid_header(), 'Student Name', activity.short_name])
    
    student_members = Member.objects.filter(offering = course, role = 'STUD').select_related('person')
    for std in student_members:
        row = [std.person.emplid, std.person.userid, std.person.name()]
        try: 
            lgrade = LetterGrade.objects.get(activity = activity, member = std)                  
        except LetterGrade.DoesNotExist: #if the LetterGrade does not exist yet,
            row.append('')
        else:
            if lgrade.flag == 'GRAD' or lgrade.flag == 'CALC':
                row.append(lgrade.letter_grade)
            elif lgrade.flag == 'NOGR':
                row.append('')
            else:
                row.append(lgrade.flag)
        
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
def export_sims(request, course_slug, activity_slug):
    """
    Produce CSV export format for SIMS/goSFU.
    """
    course = get_object_or_404(CourseOffering, slug = course_slug)    
    activity = get_object_or_404(LetterActivity, offering = course, slug = activity_slug, deleted=False)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s_%s_sims.csv"' % (course_slug, activity_slug,)
    
    writer = csv.writer(response)
    student_members = Member.objects.filter(offering = course, role = 'STUD').select_related('person')
    section_cache = {}
    for std in student_members:
        c = course
        # if we have an origsection (because this student was combined in a joint offering), honour it.
        if 'origsection' in std.config:
            origslug = std.config['origsection']
            if origslug in section_cache:
                c = section_cache[origslug]
            else:
                c = std.get_origsection()
                section_cache[origslug] = c

        row = [c.subject, c.number, c.section, std.person.emplid]
        try: 
            lgrade = LetterGrade.objects.get(activity = activity, member = std)                  
        except LetterGrade.DoesNotExist: #if the LetterGrade does not exist yet,
            row.append('')
        else:
            if lgrade.flag == 'NOGR':
                row.append('')
            else:
                row.append(lgrade.letter_grade)
        
        row.append(std.person.name())
        row.append(std.person.userid)
        writer.writerow(row)

    return response



@requires_course_staff_by_slug
@uses_feature('marking')
def mark_all_groups(request, course_slug, activity_slug):
    """
    Mark the whole class (by group).  Calls numeric/letter view as appropriate.
    """
    course = get_object_or_404(CourseOffering, slug = course_slug)
    acts = all_activities_filter(course, slug=activity_slug)
    if len(acts) != 1:
        raise Http404('No such Activity.')
    activity = acts[0]
    
    if isinstance(activity, NumericActivity):
        return _mark_all_groups_numeric(request, course, activity)
    elif isinstance(activity, LetterActivity):
        return _mark_all_groups_letter(request, course, activity)
    else:
        raise Http404('Unknown activity type.')


@transaction.atomic
def _mark_all_groups_numeric(request, course, activity):
    error_info = None
    rows=[]
    warning_info=[]
    groups = set()
    all_members = GroupMember.objects.select_related('group').filter(activity = activity, confirmed = True)
    for member in all_members:
        if not member.group in groups:
            groups.add(member.group)
    
    if request.method == 'POST':
        entered_by = get_entry_person(request.user.username)
        current_act_marks = []
        for group in groups:
            entry_form = MarkEntryForm(data = request.POST, prefix = group.name)
            if not entry_form.is_valid():
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
                act_mark.setMark(new_value, entered_by=entered_by, details=False)
                act_mark.save()

                updated += 1
                if new_value < 0:
                    warning_info.append(u"Negative mark given to group %s" % group.name)
                elif new_value > activity.max_grade:
                    warning_info.append(u"Bonus mark given to group %s" % group.name)  

                #LOG EVENT
                l = LogEntry(userid=request.user.username,
                     description=(u"bulk marked %s for group '%s': %s/%s") % (activity, group.name, new_value, activity.max_grade),
                     related_object=act_mark)
                l.save()                  
                 
            if updated > 0:
                messages.add_message(request, messages.SUCCESS, u"Marks for all groups on %s saved (%s groups' grades updated)!" % (activity.name, updated))
            for warning in warning_info:
                messages.add_message(request, messages.WARNING, warning)                    
            return _redirct_response(request, course.slug, activity.slug)   
        
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


@transaction.atomic
def _mark_all_groups_letter(request, course, activity):
    error_info = None
    rows=[]
    warning_info=[]
    groups = set()
    all_members = GroupMember.objects.select_related('group').filter(activity = activity, confirmed = True)
    for member in all_members:
        if not member.group in groups:
            groups.add(member.group)
    
    if request.method == 'POST':
        entered_by = get_entry_person(request.user.username)
        current_act_marks = []
        for group in groups:
            entry_form = MarkEntryForm_LetterGrade(data = request.POST, prefix = group.name)
            if not entry_form.is_valid():
                error_info = "Error found"           
            act_mark = None 
            try:
                act_mark = LetterGrade.objects.get(activity = activity, member = member)
            except LetterGrade.DoesNotExist:
                current_grade = 'no grade'
            else:
                current_grade = act_mark.letter_grade   
            current_act_marks.append(act_mark)
            rows.append({'group': group, 'current_grade' : current_grade, 'form' : entry_form})  
        
        if error_info == None:
            updated = 0
            i = -1
            for group in groups:
                i += 1
                act_mark=current_act_marks[i]
                new_value = rows[i]['form'].cleaned_data['value']
                if new_value not in LETTER_GRADE_CHOICES_IN: 
                    continue
                if act_mark!= None and act_mark.letter_grade == new_value:
                    # if any of the group members originally has a grade status other than 'GRAD'
                    # so do not override the status
                    continue
                #if act_mark == None:
                #act_mark = LetterGrade(activity = activity, member = all_members[i])       
                act_mark = GroupActivityMark_LetterGrade(group=group, letter_activity=activity, created_by=request.user.username)
                act_mark.setMark(new_value, entered_by=entered_by)
                act_mark.save()

                #LOG EVENT
                l = LogEntry(userid=request.user.username,
                     description=("bulk marked %s for group '%s': %s") % (activity, group.name, new_value),
                     related_object=act_mark)
                l.save()                  
                 
            if updated > 0:
                messages.add_message(request, messages.SUCCESS, "Marks for all groups on %s saved (%s groups' grades updated)!" % (activity.name, updated))
            for warning in warning_info:
                messages.add_message(request, messages.WARNING, warning)                    
            return _redirct_response(request, course.slug, activity.slug)   
        
    else: # for GET request
        for group in groups:
            act_mark = get_group_mark(activity, group)
            if act_mark == None:
                current_grade = 'no grade'
            else:
                current_grade = act_mark.mark
            entry_form = MarkEntryForm_LetterGrade(prefix=group.name)                                    
            rows.append({'group': group, 'current_grade' : current_grade, 'form' : entry_form}) 
        
    
    if error_info:
        messages.add_message(request, messages.ERROR, error_info)     
    return render_to_response("marking/mark_all_group_lettergrade.html",
                          {'course': course, 'activity': activity,'mark_all_rows': rows }, 
                          context_instance = RequestContext(request))     

#This is for change grade status of letter grades


@transaction.atomic
def _mark_all_students_letter(request, course, activity):
    rows = []
    fileform = None
    imported_data = {} #may get filled with data from an imported file, a mapping from student's userid to grade
    error_info = None 
    warning_info = []
    memberships = Member.objects.select_related('person').filter(offering = course, role = 'STUD')
    valid_input = True  
    
    if request.method == 'POST' and request.GET.get('import') != 'true':
        lgrades = []   
        # get data from the mark entry forms
        for member in memberships: 
            student = member.person  
            entry_form = MarkEntryForm_LetterGrade(data = request.POST, prefix = student.userid)
            if not entry_form.is_valid():
                error_info = "Error found"           
            lgrade = None
            try:
                lgrade = LetterGrade.objects.get(activity = activity, member = member)
            except LetterGrade.DoesNotExist:
                current_grade = 'no grade'
            else:
                current_grade = lgrade.letter_grade                    
            lgrades.append(lgrade) 
            rows.append({'student': student, 'member': member, 'current_grade' : current_grade, 'form' : entry_form})    
       
        # save if needed 
        if error_info == None:
            entered_by = get_entry_person(request.user.username)
            updated = 0                 
            for i in range(len(memberships)):
                student = memberships[i].person  
                lgrade = lgrades[i]
                new_value = rows[i]['form'].cleaned_data['value'] 
                # the new mark is blank or the new mark is the same as the old one, do nothing
                if new_value not in LETTER_GRADE_CHOICES_IN:  
                    error_info = False
                    continue
                if lgrade !=None and lgrade.letter_grade == new_value:
                    # if the student originally has a grade status other than 'GRAD',
                    # we do not override that status
                    continue 
                # save data 
                if lgrade == None:
                    lgrade = LetterGrade(activity = activity, member = memberships[i]);
                lgrade.letter_grade = new_value
                lgrade.flag = "GRAD"
                lgrade.save(entered_by=entered_by)
               
                updated += 1    
               
               
                #LOG EVENT
                l = LogEntry(userid=request.user.username,
                     description=(u"bulk marked %s for %s: %s") % (activity, student.userid, new_value),
                     related_object=lgrade)
                l.save()                  
           
            if updated > 0:
                messages.add_message(request, messages.SUCCESS, u"Marks for all students on %s saved (%s students' grades updated)!" % (activity.name, updated))
            
            #if valid_input == False:
            #   messages.add_message(request, messages.SUCCESS, "Not valid input exists, but was ignored. Please check for not updated one.")
                    
            return _redirct_response(request, course.slug, activity.slug) 
    
    else: 
        if request.method == 'POST': # for import
            fileform = UploadGradeFileForm_LetterGrade(request.POST, request.FILES, prefix = 'import-file');
            if fileform.is_valid() and fileform.cleaned_data['file'] != None:
                students = course.members.filter(person__role='STUD')
                error_info = _compose_imported_grades(fileform.cleaned_data['file'], students, imported_data, activity)
                if error_info == None:
                    messages.add_message(request, messages.SUCCESS,\
                                "%s students' grades imported. Please review before submitting." % len(imported_data.keys()))
        # may use the imported file data to fill in the forms       
        for member in memberships: 
            student = member.person              
            try:
                lgrade = LetterGrade.objects.get(activity = activity, member = member)
            except LetterGrade.DoesNotExist:
                current_grade = 'no grade'
            else:
                current_grade = lgrade.letter_grade            
            initial_value = imported_data.get(student.userid) 
            if initial_value != None:
                entry_form = MarkEntryForm_LetterGrade(initial = {'value': initial_value}, prefix = student.userid)
            else:
                entry_form = MarkEntryForm_LetterGrade(prefix = student.userid)                                    
            rows.append({'student': student, 'member': member, 'current_grade' : current_grade, 'form' : entry_form}) 
               
    if error_info:
        messages.add_message(request, messages.ERROR, error_info) 

    if fileform == None:
        fileform = UploadGradeFileForm_LetterGrade(prefix = 'import-file')   

    return render_to_response("marking/mark_all_student_lettergrade.html",{'course': course, 'activity': activity,
                              'fileform' : fileform,'too_many': len(rows) >= 100,
                              'mark_all_rows': rows, 'userid_header': Person.userid_header() }, 
                              context_instance = RequestContext(request))



@requires_course_staff_by_slug
@uses_feature('marking')
def calculate_lettergrade(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(LetterActivity, offering = course, slug = activity_slug, deleted=False)



















@requires_course_staff_by_slug
@uses_feature('marking')
def mark_all_students(request, course_slug, activity_slug):
    """
    Mark the whole class (by student).  Calls numeric/letter view as appropriate.
    """
    course = get_object_or_404(CourseOffering, slug = course_slug)
    acts = all_activities_filter(course, slug=activity_slug)
    if len(acts) != 1:
        raise Http404('No such Activity.')
    activity = acts[0]
    
    if isinstance(activity, NumericActivity):
        return _mark_all_students_numeric(request, course, activity)
    elif isinstance(activity, LetterActivity):
        return _mark_all_students_letter(request, course, activity)
    else:
        raise Http404('Unknown activity type.')

   
@transaction.atomic
def _mark_all_students_numeric(request, course, activity):
    rows = []
    fileform = None
    imported_data = {} #may get filled with data from an imported file, a mapping from student's userid to grade
    error_info = None 
    warning_info = []
    memberships = Member.objects.select_related('person').filter(offering=course, role='STUD')   
    
    if request.method == 'POST' and request.GET.get('import') != 'true':
        ngrades = []   
        # get data from the mark entry forms
        for member in memberships: 
            student = member.person  
            entry_form = MarkEntryForm(data = request.POST, prefix=student.userid)
            if not entry_form.is_valid():
                error_info = "Error found"           
            ngrade = None
            try:
                ngrade = NumericGrade.objects.get(activity=activity, member=member)
            except NumericGrade.DoesNotExist:
                current_grade = 'no grade'
            else:
                current_grade = ngrade.value                    
            ngrades.append(ngrade) 
            rows.append({'student': student, 'member': member, 'current_grade' : current_grade, 'form' : entry_form})

        # save if needed 
        if error_info == None:
            entered_by = get_entry_person(request.user.username)
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
                ngrade.save(entered_by=entered_by)
                
                updated += 1     
                if new_value < 0:
                    warning_info.append(u"Negative mark given to %s on %s" %(student.userid, activity.name))
                elif new_value > activity.max_grade:
                    warning_info.append(u"Bonus mark given to %s on %s" %(student.userid, activity.name))
               
                #LOG EVENT
                l = LogEntry(userid=request.user.username,
                      description=(u"bulk marked %s for %s: %s/%s") % (activity, student.userid, new_value, activity.max_grade),
                      related_object=ngrade)
                l.save()                  
           
            if updated > 0:
                messages.add_message(request, messages.SUCCESS, "Marks for all students on %s saved (%s students' grades updated)!" % (activity.name, updated))
                for warning in warning_info:
                    messages.add_message(request, messages.WARNING, warning)
                    
            return _redirct_response(request, course.slug, activity.slug) 
    
    else: 
        if request.method == 'POST': # for import
            fileform = UploadGradeFileForm(request.POST, request.FILES, prefix='import-file');
            if fileform.is_valid() and fileform.cleaned_data['file'] != None:
                students = course.members.filter(person__role='STUD')
                error_info = _compose_imported_grades(fileform.cleaned_data['file'], students, imported_data, activity)
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
            rows.append({'student': student, 'member': member, 'current_grade' : current_grade, 'form' : entry_form}) 
               
    if error_info:
        messages.add_message(request, messages.ERROR, error_info) 

    if fileform == None:
        fileform = UploadGradeFileForm(prefix = 'import-file')   
    
    return render_to_response("marking/mark_all_student.html",{'course': course, 'activity': activity,
                              'fileform' : fileform,'too_many': len(rows) >= 100,
                              'mark_all_rows': rows, 'userid_header': Person.userid_header()},
                              context_instance = RequestContext(request))

def _compose_imported_grades(file, students_qset, data_to_return, activity):
    try:
        fh = io.StringIO(file.read().decode('utf-8'), newline=None)
    except UnicodeDecodeError:
        error_string = "File cannot be decoded as UTF-8 data: make sure it has been saved as UTF-8 text."
    else:
        fcopy = io.StringIO(fh.getvalue(), newline=None)
        try:
            first_line = csv.reader(fcopy).next()
            (error_string, userid_col, activity_col) = _CMS_header(first_line, Person.userid_header(), activity.short_name)
        except UnicodeEncodeError:
            error_string = "File cannot be encoded as UTF-8 data: make sure it contains legal Unicode characters."

    if error_string != None:
        return error_string
    elif userid_col != None and activity_col != None:
        try:
            return _import_CMS_output(fh, students_qset, data_to_return, userid_col, activity_col)
        except UnicodeEncodeError:
            return "File contains bad UTF-8 data: make sure it has been saved as UTF-8 text."
    else:
        return _import_specific_file(fh, students_qset, data_to_return)

def _CMS_header(line, userid_label, act_label):
    userid_col = None
    activity_col = None
    for lcol, label in enumerate(line):
        if label == userid_label:
            if userid_col == None:
                userid_col = lcol
            else:
                error_string = "Error in file header line:  Two columns labelled " + userid_label + "."
                return (error_string, None, None)
        elif label == act_label:
            if activity_col == None:
                activity_col = lcol
            else:
                error_string = "Error in file header line:  Two columns labelled " + act_label + "."
                return (error_string, None, None)
    if userid_col != None and activity_col == None:
        return ('Error in file header line:  No column labelled for activity ' + act_label + '.', None, None)
    return (None, userid_col, activity_col)

def _strip_email_userid(s):
    """
    Accept "userid@sfu.ca" as "userid".  Return userid in any case.
    """
    DOMAIN = "sfu.ca"
    if s.endswith("@"+DOMAIN):
        return s[:-(len(DOMAIN)+1)]
    return s

def _import_CMS_output(fh, students_qset, data_to_return, userid_col, activity_col):
    reader = csv.reader(fh)
    reader.next() # Skip header line
    #print userid_col, activity_col #AEK
    for row_num, row in enumerate(reader):
        #print row_num, row #AEK
        userid = _strip_email_userid(row[userid_col])
        target = students_qset.filter(userid = userid)
        if target.count() == 0:
            data_to_return.clear()
            return u"Error found in file (row %s): Unmatched userid (%s)." % (row_num, row[userid_col])
        if data_to_return.has_key(target[0].userid):
            data_to_return.clear()
            return u"Error found in file (row %s): Second entry found for student (%s)." % (row_num, row[userid_col])
        try:
            data_to_return[target[0].userid] = row[activity_col]
        except IndexError:
            # short row: no data
            pass
    return None

def _import_specific_file(fh, students_qset, data_to_return):
    reader = csv.reader(fh)   
    try:  
        read = 1;
        for row in reader:            
            try: #if the first field is not an integer, cannot be emplid
                userid = _strip_email_userid(row[0])
                num = int(row[0])
            except ValueError:
                target = students_qset.filter(userid = userid)
            else:        
                target = students_qset.filter(Q(userid = userid) | Q(emplid = num))
            if target.count() == 0:                
                data_to_return.clear()
                return u"Error found in the file (row %s): Unmatched student number or user-id (%s)." % (read, row[0],)            
            if(data_to_return.has_key(target[0].userid)):
                data_to_return.clear()
                return u"Error found in the file (row %s): Second entry found for student (%s)." % (read, row[0],) 
            data_to_return[target[0].userid] = row[1]
            read += 1               
    except:
        data_to_return.clear()
        return ("Error found in the file (row %s): The format should be " % read) +\
               "\"[student user-id or student number, grade, ]\" and " + \
               "only the first two columns are used."   
    return None   

# adapted from http://stackoverflow.com/questions/1960516/python-json-serialize-a-decimal-object
class _DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(_DecimalEncoder, self).default(o)

def _export_mark_dict(m):
    """
    Dictionary required for JSON export of ActivityMark (without userid/group identifier)
    """
    mdict = {}
    comps = ActivityComponentMark.objects.filter(activity_mark=m).select_related('activity_component')
    for c in comps:
        mdict[c.activity_component.slug] = {'mark': c.value}
        mdict[c.activity_component.slug]['comment'] = c.comment
        
    mdict['late_percent'] = m.late_penalty
    mdict['mark_penalty'] = m.mark_adjustment
    mdict['mark_penalty_reason'] = m.mark_adjustment_reason
    mdict['overall_comment'] = m.overall_comment
    
    return mdict


def _mark_export_data(activity):
    data = []
    found = set()
    marks = StudentActivityMark.objects.filter(numeric_grade__activity=activity).order_by('-created_at')
    for m in marks:
        ident = m.numeric_grade.member.person.userid
        if ident in found:
            continue
        found.add(ident)
        mdict = _export_mark_dict(m)
        mdict['userid'] = ident
        data.append(mdict)
    marks = GroupActivityMark.objects.filter(numeric_activity=activity).order_by('-created_at')
    for m in marks:
        ident = m.group.slug
        if ident in found:
            continue
        found.add(ident)
        mdict = _export_mark_dict(m)
        mdict['group'] = ident
        data.append(mdict)
    
    return data

@requires_course_staff_by_slug
def export_marks(request, course_slug, activity_slug):
    """
    Export JSON marking data
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    acts = all_activities_filter(course, slug=activity_slug)
    if len(acts) != 1:
        raise Http404('No such Activity.')
    activity = acts[0]
    
    data = _mark_export_data(activity)
    response = HttpResponse(content_type='application/json')
    response['Content-Disposition'] = 'inline; filename="%s-%s.json"' % (course.slug, activity.slug)
    
    json.dump({'marks': data}, response, cls=_DecimalEncoder, indent=1)
    
    return response




@requires_course_staff_by_slug
@transaction.atomic
@uses_feature('marking')
def import_marks(request, course_slug, activity_slug):
    """
    Import JSON marking data
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    acts = all_activities_filter(course, slug=activity_slug)
    if len(acts) != 1:
        raise Http404('No such Activity.')
    activity = acts[0]
    
    if request.method == 'POST':
        form = ImportMarkFileForm(data=request.POST, files=request.FILES, activity=activity, userid=request.user.username)
        if form.is_valid():
            entered_by = get_entry_person(request.user.username)
            # validation function builds all the objects we need: just save them now that we know everything is okay.
            ams, amcs, ngs = form.cleaned_data['file']
            count = 0
            for ng in ngs:
                # save temporarily so we have ids for foreign keys
                ng.flag = 'NOGR'
                ng.save(entered_by=None, is_temporary=True)

            for am in ams:
                if isinstance(am, StudentActivityMark):
                    am.numeric_grade = am.numeric_grade
                    #LOG EVENT
                    l = LogEntry(userid=request.user.username,
                          description=(u"Imported marking info for student %s on %s in %s") % (am.numeric_grade.member.person.userid, activity, course),
                          related_object=activity)
                    l.save()
                else:
                    #LOG EVENT
                    l = LogEntry(userid=request.user.username,
                          description=(u"Imported marking info for group %s on %s in %s") % (am.group.slug, activity, course),
                          related_object=activity)
                    l.save()

                am.setMark(am.mark, entered_by=entered_by) # deal with the GradeHistory and other details
                am.save()
                count += 1

            for amc in amcs:
                amc.activity_mark = amc.activity_mark
                amc.save()

            messages.add_message(request, messages.SUCCESS, "Successfully imported %i marks." % (count))
            
            return _redirct_response(request, course_slug, activity_slug)
    else:
        form = ImportMarkFileForm(activity=activity, userid=request.user.username)
    
    groups = None
    if activity.group:
        # collect groups so we can report slugs
        groups = set((gm.group for gm in GroupMember.objects.filter(activity=activity).select_related('group')))
    
    components = ActivityComponent.objects.filter(numeric_activity=activity, deleted=False)
    context = {'course': course, 'activity': activity, 'components': components, 'groups': groups, 'form': form}
    return render_to_response("marking/import_marks.html", context, context_instance=RequestContext(request))

