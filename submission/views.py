from courses.submission.models import GroupSubmission
from django.contrib.auth.decorators import login_required
from coredata.models import Member, CourseOffering, Person
from django.shortcuts import render_to_response, get_object_or_404#, redirect
from django.template import RequestContext
from django.http import HttpResponseRedirect, QueryDict
from courselib.auth import requires_course_by_slug,requires_course_staff_by_slug, ForbiddenResponse, NotFoundResponse
from submission.forms import *
from courselib.auth import is_course_staff_by_slug, is_course_member_by_slug
from submission.models import *
from django.core.urlresolvers import reverse
from contrib import messages
from datetime import *
from marking.views import marking_student, marking_group
from groups.models import Group, GroupMember
from log.models import LogEntry

#@login_required
#def index(request):
#    userid = request.user.username
#    memberships = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=userid) \
#            .select_related('offering','person','offering__semester')
#    return render_to_response("submission/index.html", {'memberships': memberships}, context_instance=RequestContext(request))


@login_required
def show_components(request, course_slug, activity_slug):
    #if course staff
    if is_course_staff_by_slug(request.user, course_slug):
        return _show_components_staff(request, course_slug, activity_slug)
    #else course member
    elif is_course_member_by_slug(request.user, course_slug):
        return _show_components_student(request, course_slug, activity_slug)
    #else not found, return 403
    else:
        return ForbiddenResponse(request);
    
#student submission main page
#may be viewed by a staff
def _show_components_student(request, course_slug, activity_slug, userid=None, template="dashboard_student.html"):
    """
    Show all the component submission history of this activity
    """
    if userid == None:
        userid = request.user.username
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug)
    student = get_object_or_404(Person, userid=userid)
    cansubmit = True

    submission, submitted_components = get_current_submission(student, activity)
    if len(submitted_components) == 0:
        return NotFoundResponse(request)

    if submission and activity.due_date and activity.due_date < submission.created_at:
        late = submission.created_at - activity.due_date
    else:
        late = 0

    if activity.group:
        gm = GroupMember.objects.filter(student__person=student, activity=activity, confirmed=True)
        if gm:
            group = gm[0].group
            messages.add_message(request, messages.WARNING, "This is a group submission. You will submit on behalf of the group %s." % group.name)
        else:
            group = None
            cansubmit = False
            messages.add_message(request, messages.WARNING, "This is a group submission. You cannot submit since you aren't in a group.")
    else:
        group = None

    # activity should be submitable
    cansubmit = cansubmit and activity.submitable()
    
    return render_to_response("submission/" + template,
        {"course":course, "activity":activity, "submission": submission, "submitted_components":submitted_components, "userid":userid, "late":late, "student":student, "group":group, "cansubmit":cansubmit},
        context_instance=RequestContext(request))


#student's submission page
@requires_course_by_slug
def add_submission(request, course_slug, activity_slug):
    """
    enable student to upload files to a activity
    """
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug)
    component_list = select_all_components(activity)
    component_list.sort()
    component_form_list=[]

    if not activity.submitable():
        messages.add_message(request, messages.ERROR, "This activity is not submittable.")
        return ForbiddenResponse(request)

    group_member = None
    if activity.group:
        group_member = GroupMember.objects.filter(student__person__userid=request.user.username)\
                                            .filter(confirmed=True)\
                                            .filter(activity=activity)
        if len(group_member) > 0:
            group_member = group_member[0]

    if request.method == 'POST':
        component_form_list = make_form_from_list(component_list, request=request)
        submitted_comp = []    # list all components which has content submitted in the POST
        not_submitted_comp = [] #list allcomponents which has no content submitted in the POST
        if not activity.group:
            new_sub = StudentSubmission()   # the submission foreign key for newly submitted components
            new_sub.member = get_object_or_404(Member, offering__slug=course_slug, person__userid=request.user.username)
        elif group_member:
            new_sub = GroupSubmission()
            new_sub.group = group_member.group
            new_sub.creator = group_member.student
        else:
            messages.add_message(request, messages.ERROR, "This is a group submission. You cannot submit since you aren't in a group.")
            return ForbiddenResponse(request)
        new_sub.activity = activity
        new_sub_saved = False
        
        for data in component_form_list:
            component = data['comp']
            form = data['form']

            #form[1].component = form[0]
            if form.is_valid():
                #save the foreign submission first at the first time a submission component is read in
                if new_sub_saved == False:
                    # save the submission forgein key
                    new_sub_saved = True
                    new_sub.save()
                
                sub = form.save(commit=False)
                sub.submission = new_sub
                sub.component = component
                sub.save()
                
                submitted_comp.append(sub)
                #LOG EVENT#
                if activity.group:
                    group_str = " as a member of group %s" % new_sub.group.name
                else:
                    group_str = ""
                l = LogEntry(userid=request.user.username,
                      description=("submitted for %s %s" + group_str) % (activity, sub.component.title),
                      related_object=sub)
                l.save()
            else:
                not_submitted_comp.append(component)
        
        if len(not_submitted_comp) == 0:
            messages.add_message(request, messages.SUCCESS, "Your submission was successful.")
            return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))
        
        return render_to_response("submission/submission_error.html",
            {"course":course, "activity":activity, "component_list":component_form_list,
            "submitted_comp":submitted_comp, "not_submitted_comp":not_submitted_comp},
            context_instance=RequestContext(request))
    else: #not POST
        #print activity.group, group_member
        if activity.group and group_member:
            messages.add_message(request, messages.WARNING, "This is a group submission. Your will submit on behalf of all your group members.")
        elif activity.group:
            return ForbiddenResponse(request)

        component_form_list = make_form_from_list(component_list)
        return render_to_response("submission/submission_add.html",
        {'component_form_list': component_form_list, "course": course, "activity": activity},
        context_instance = RequestContext(request))

def XXXX_check_me_or_member(request, target_uid, course, activity, staff=True):
    """
    if it's me or it's a member of my group, return true; otherwise false;
    staff=True means staff will always return true
    """
    get_object_or_404(Person, userid=target_uid)
    if target_uid == request.user.username:
        return True
    if is_course_staff_by_slug(request.user, course.slug):
        return staff
    my_group = GroupMember.objects.all().filter(student__person__userid=request.user.username).filter(activity=activity)
    if len(my_group) != 0:
        target_group = GroupMember.objects.all().filter(student__person__userid=target_uid).filter(activity=activity)
        if len(target_group) != 0:
            if target_group[0].group == my_group[0].group:
                return True
    return False

@requires_course_by_slug
def show_components_submission_history(request, course_slug, activity_slug, userid=None):
    if userid is None:
        userid = request.GET.get('userid')
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug)

    if userid is None:
        # can always see your own submissions
        userid = request.user.username
    else:
        # specifying a userid: must be course staff
        if not is_course_staff_by_slug(request.user, course.slug):
            return ForbiddenResponse(request)

    if activity.group:
        messages.add_message(request, messages.INFO, "This is a group submission. This history is based on submissions from all your group members.")
        gms = GroupMember.objects.filter(student__person__userid=userid, confirmed=True, activity=activity)
        submissions = GroupSubmission.objects.filter(activity=activity, group__groupmember__in=gms)
    else:
        submissions = StudentSubmission.objects.filter(activity=activity, member__person__userid=userid)

    # get all submission components
    component_list = select_all_components(activity)
    all_submitted_components = []
    for submission in submissions:
        c = get_submission_components(submission, activity, component_list)
        all_submitted_components.append({'sub':submission, 'comp':c})
    
    #empty_component = []
    #for component in component_list:
    #    if select_students_submission_by_component(component, userid) == []:
    #        empty_component.append(component)
    #        messages.add_message(request, messages.WARNING, "You have no submission for "+component.title+".")
    return render_to_response("submission/submission_history_view.html", 
        {"course":course, "activity":activity,'userid':userid,'submitted_components': all_submitted_components, 'course':course, 'activity':activity},
        context_instance = RequestContext(request))

#staff submission configuratiton
def _show_components_staff(request, course_slug, activity_slug):
    """
    Show all the components of this activity
    Responsible for updating position
    """
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug)

    #if POST, update the positions
    if request.method == 'POST':
        component_list = select_all_components(activity, include_deleted=True)
        counter = 0
        for component in component_list:
            counter = counter + 1
            t = request.POST.get('' + str(counter) + '_position');
            #in case t is not a number
            try:
                component.position = int(t)
                component.save()
            except:
                pass
        messages.add_message(request, messages.SUCCESS, 'Component positions updated.')
        return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))
    
    component_list = select_all_components(activity, include_deleted=True)
    return render_to_response("submission/component_view_staff.html",
        {"course":course, "activity":activity, "component_list":component_list},
        context_instance=RequestContext(request))


#@requires_course_staff_by_slug
#def confirm_remove(request, course_slug, activity_slug):
#    course = get_object_or_404(CourseOffering, slug=course_slug)
#    activity = get_object_or_404(course.activity_set, slug = activity_slug)
#    component_list = select_all_components(activity)
    
#    #show confirm message
#    del_id = request.GET.get('id')
#    del_type = request.GET.get('type')
#    component = check_component_id_type_activity(component_list, del_id, del_type, activity)

#    #if confirmed
#    if request.method == 'POST' and component != None:
#        component.delete()
#        #LOG EVENT#
#        l = LogEntry(userid=request.user.username,
#              description=("deleted %s component %s") % (activity, component.title),
#              related_object=component)
#        l.save()
#        messages.add_message(request, messages.SUCCESS, 'Component "' +  component.title + '" removed.')
#        return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))

#    return render_to_response("submission/component_remove.html",
#            {"course":course, "activity":activity, "component":component, "del_id":del_id},
#            context_instance=RequestContext(request))


@requires_course_staff_by_slug
def edit_single(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug)
    component_list = select_all_components(activity)

    #get component
    edit_id = request.GET.get('id')
    component = get_component(activity=activity, id=edit_id)
    if component is None:
        return NotFoundResponse(request)

    form = component.Type.ComponentForm(instance=component)
    
    #get type change
    #type = request.GET.get('to_type')
    #if no type change
    #if type == None:
    #    pass
    #elif type == component.get_type():
    #    #no change
    #    return HttpResponseRedirect("?type="+type+"&id="+str(component.id))
    #else:
    #if need to change type
    #    if type == 'Archive':
    #        new_component = ArchiveComponent()
    #    elif type == 'URL':
    #        new_component = URLComponent()
    #    elif type == 'Cpp':
    #        new_component = CppComponent()
    #    elif type == 'PlainText':
    #        new_component = PlainTextComponent()
    #    elif type == 'Java':
    #        new_component = JavaComponent()
    #    else:
    #        #to_type is invalid, just ignore
    #        new_component = component
    #    #copy a new component
    #    new_component.id = component.id
    #    new_component.activity = component.activity
    #    new_component.title = component.title
    #    new_component.description = component.description
    #    new_component.position = component.position
    #    #save new component
    #    component.delete()
    #    new_component.save()
    #    #LOG EVENT#
    #    l = LogEntry(userid=request.user.username,
    #          description=("changed type of component %s of %s from %s to %s") % (component.title, activity, component.get_type(), new_component.get_type()),
    #          related_object=new_component)
    #    l.save()
    #    #refresh the form
    #    return HttpResponseRedirect("?type="+new_component.get_type()+"&id="+str(new_component.id))
        
            
    #if form submitted
    if request.method == 'POST':
        new_form = component.Type.ComponentForm(request.POST)
        if new_form.is_valid():
            new_component = new_form.save(commit=False)
            new_component.activity = activity
            new_component.id = component.id
            if new_component.position == None:
                count = len(select_all_components(activity))
                new_component.position = count + 1
            new_component.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("edited component %s of %s") % (component.title, activity),
                  related_object=new_component)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Component "' + new_component.title + '" successfully updated.')
            return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))
        else:
            form = new_form
            messages.add_message(request, messages.ERROR, 'Please correct the errors in the form.')

    #render the page
    return render_to_response("submission/component_edit_single.html",
            {"course":course, "activity":activity, "component":component, "edit_id":edit_id, "form":form},
            context_instance=RequestContext(request))

@requires_course_staff_by_slug
def add_component(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug)

    #default, Archive
    typelabel = request.GET.get('type')
    if typelabel == None:
        Type = Archive
    else:
        Type = find_type_by_label(typelabel)
    
    if Type is None:
        return NotFoundResponse(request)
    
    form = Type.ComponentForm()

    #if form is submitted, validate / add component
    if request.method == 'POST':
        new_form = Type.ComponentForm(request.POST)
        if new_form.is_valid():
            #add component
            new_component = new_form.save(commit=False)
            new_component.activity = activity
            new_component.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
                  description=("added %s component %s for %s") % (Type.name, new_component.title, activity),
                  related_object=new_component)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'New component "' + new_component.title + '" successfully added.')
            return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))
        else:
            messages.add_message(request, messages.ERROR, 'Please correct the errors in the form.')
            form = new_form
    return render_to_response("submission/component_add.html", 
        {"course":course, "activity":activity, "form":form, "type":Type, "types": ALL_TYPE_CLASSES},
        context_instance=RequestContext(request))

def get_submission(submission_id):
    try:
        return StudentSubmission.objects.get(id=submission_id)
    except StudentSubmission.DoesNotExist:
        try:
            return GroupSubmission.objects.get(id=submission_id)
        except GroupSubmission.DoesNotExist:
            return None
    


@requires_course_by_slug
def download_file(request, course_slug, activity_slug, component_slug=None, submission_id=None, userid=None):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug)
    
    # find the appropriate submission object
    if submission_id:
        # explicit request: get that one.
        submission = get_submission(submission_id)
        if not submission or submission.activity!=activity:
            return NotFoundResponse(request)
        submitted_components = get_submission_components(submission, activity)

    elif userid:
        # userid specified: get their most recent submission
        student = get_object_or_404(Person, userid=userid)
        submission, submitted_components = get_current_submission(student, activity)
        if not submission:
            return NotFoundResponse(request)
    
    else:
        return NotFoundResponse(request)

    
    # make sure this user is allowed to see the file
    if is_course_staff_by_slug(request.user, course_slug):
        pass
    elif isinstance(submission, GroupSubmission):
        membership = submission.group.groupmember_set.filter(student__person__userid=request.user.username, confirmed=True)
        if not membership:
            return ForbiddenResponse(request)
    elif isinstance(submission, StudentSubmission):
        if submission.member.person.userid != request.user.username:
            return ForbiddenResponse(request)

    # create the result
    if component_slug:
        # download single component if specified
        # get the actual component: already did the searching above, so just look in that list
        components = [sub for comp,sub in submitted_components if sub and sub.component.slug==component_slug]
        if not components:
            return NotFoundResponse(request)
        return components[0].download_response()
    else:
        # no component specified: give back the full ZIP file.
        return generate_zip_file(submission, submitted_components)

    #if no_submission == True:
    #    return render_to_response("submission/download_error_no_submission.html",
    #    {"course":course, "activity":activity, "student":student},
    #    context_instance=RequestContext(request))

@requires_course_staff_by_slug
def show_student_submission_staff(request, course_slug, activity_slug, userid):
    return _show_components_student(request, course_slug, activity_slug, userid, "view_student_dashboard_staff.html")

@requires_course_staff_by_slug
def show_student_history_staff(request, course_slug, activity_slug, userid):
    return show_components_submission_history(request, course_slug, activity_slug, userid)

@requires_course_staff_by_slug
def take_ownership_and_mark(request, course_slug, activity_slug, userid=None, group_slug=None):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug=activity_slug)

    # get the urlencode
    qDict = request.GET
    urlencode = ''
    if qDict.items():
        urlencode = '?' +  qDict.urlencode()

    if userid:
        try:
            if activity.group is True:
                member = GroupMember.objects.filter(activity=activity, student__person__userid=userid, confirmed=True)
                submission = GroupSubmission.objects.filter(activity=activity, group=member[0].group).latest('created_at')
                print submission
            else:
                submission = StudentSubmission.objects.filter(activity=activity, member__person__userid=userid).latest('created_at')
        except:
            submission = None
        response = HttpResponseRedirect(reverse(marking_student, args=[course_slug, activity_slug, userid]) + urlencode)
        #if it is taken by someone not me, show a confirm dialog
        if request.GET.get('confirm') == None:
            if submission and submission.owner:
                return _override_ownership_confirm(request, course, activity, userid, None, submission.owner.person, urlencode[1:])

        if submission:
            submission.set_owner(course, request.user.username)

        #LOG EVENT#
        student = get_object_or_404(Person, userid=userid)
        if submission:
            str = (" of submission %i") % (submission.id)
        else:
            str = ""
        l = LogEntry(userid=request.user.username,
              description=("took ownership on %s" + str + " by %s") % (activity, userid),
              related_object=student)
        l.save()

        return response
    elif group_slug:
        try:
            submission = GroupSubmission.objects.filter(group__slug=group_slug).latest('created_at')
        except:
            submission = None
        response = HttpResponseRedirect(reverse(marking_group, args=[course_slug, activity_slug, group_slug]) + urlencode)
        #if it is taken by someone not me, show a confirm dialog
        if request.GET.get('confirm') == None:
            if submission and submission.owner:
                return _override_ownership_confirm(request, course, activity, None, group_slug, submission.owner.person, urlencode[1:])

        if submission:
            submission.set_owner(course, request.user.username)
        #LOG EVENT#
        groups = Group.objects.all().filter(courseoffering=course)
        group = get_object_or_404(groups, slug=group_slug)
        if submission:
            str = (" of submission %i by group %s") % (submission.id, submission.file_slug)
        else:
            str = ""
        l = LogEntry(userid=request.user.username,
          description=("took ownership on %s"+str+ " by group %s") % (activity, group.name),
          related_object=group)
        l.save()
        return response
    

@requires_course_staff_by_slug
def XXX_take_ownership_and_mark_group(request, course_slug, activity_slug, group_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug)
    group = get_object_or_404(Group, slug = group_slug)

    # get the urlencode
    qDict = request.GET
    urlencode = ''
    if qDict.items():
        urlencode = '?' +  qDict.urlencode()
    
    group_member = GroupMember.objects.filter(activity__slug=activity_slug, group=group, confirmed = True)   
    response = HttpResponseRedirect(reverse(marking_group, args=[course_slug, activity_slug, group_slug]) + urlencode)
    component = select_students_submitted_components(activity, group_member[0].student.person.userid)
    #if it is taken by someone not me, show a confirm dialog
    if request.GET.get('confirm') == None:
        for c in component:
            if c.submission.owner != None and c.submission.owner.person.userid != request.user.username:
                return _override_ownership_confirm(request, course, activity, group_member[0].student.person.userid, group_slug, c.submission.owner.person, urlencode)
    for c in component:
        c.submission.set_owner(course, request.user.username)

    group = group_member[0].group
    l = LogEntry(userid=request.user.username,
          description=("took ownership on %s of submission by group %s") % (activity, group.name),
          related_object=group)
    l.save()
    return response

def _override_ownership_confirm(request, course, activity, userid, group_slug, old_owner, urlencode):
    if group_slug == None:
        group = None
        student = get_object_or_404(Person, userid=userid)
    else:
        student = None
        groups = Group.objects.all().filter(courseoffering=course)
        group = get_object_or_404(groups, slug=group_slug)
        
    
    return render_to_response("submission/override_ownership_confirm.html",
        {"course":course, "activity":activity, "student":student, "group":group, "old_owner":old_owner, "true":True, "urlencode":urlencode, "userid":userid},
        context_instance=RequestContext(request))
