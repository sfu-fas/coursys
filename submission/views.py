from django.contrib.auth.decorators import login_required
from coredata.models import Member, CourseOffering, Person
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from courselib.auth import requires_course_by_slug,requires_course_staff_by_slug, ForbiddenResponse, NotFoundResponse
from submission.forms import make_form_from_list
from courselib.auth import is_course_staff_by_slug, is_course_member_by_slug, uses_feature
from submission.models import StudentSubmission, GroupSubmission, get_current_submission, select_all_components, \
    get_submission_components, get_component, find_type_by_label, generate_activity_zip, generate_zip_file, ALL_TYPE_CLASSES
from django.core.urlresolvers import reverse
from django.contrib import messages
from marking.views import marking_student, marking_group
from groups.models import Group, GroupMember
from log.models import LogEntry
from django.forms.util import ErrorList


@login_required
def show_components(request, course_slug, activity_slug):
    #if course staff
    if is_course_staff_by_slug(request, course_slug):
        return _show_components_staff(request, course_slug, activity_slug)
    #else course member
    elif is_course_member_by_slug(request, course_slug):
        return _show_components_student(request, course_slug, activity_slug)
    #else not found, return 403
    else:
        return ForbiddenResponse(request);
    
#student submission main page
#may be viewed by a staff
def _show_components_student(request, course_slug, activity_slug, userid=None, template="dashboard_student.html", staff=False):
    """
    Show all the component submission history of this activity
    """
    if userid == None:
        userid = request.user.username
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug, deleted=False)
    student = get_object_or_404(Person, userid=userid)
    cansubmit = True

    submission, submitted_components = get_current_submission(student, activity, include_deleted=staff)
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
            member = gm[0].student
        else:
            group = None
            #cansubmit = False
            #messages.add_message(request, messages.INFO, "This is a group submission. You cannot submit since you aren't in a group.")
    else:
        group = None

    # activity should be submitable
    cansubmit = cansubmit and activity.submitable()

    if not cansubmit:
        messages.add_message(request, messages.ERROR, "This activity is not submittable.")
        return render(request, "submission/" + template,
        {"course":course, "activity":activity, "submission": submission, "submitted_components":submitted_components,
         "userid":userid, "late":late, "student":student, "group":group, "cansubmit":cansubmit})

    # get all components of activity
    component_list = select_all_components(activity)
    component_list.sort()
    component_form_list=[]

    if request.method == 'POST':
        component_form_list = make_form_from_list(component_list, request=request)
        submitted_comp = []    # list all components which has content submitted in the POST
        not_submitted_comp = [] #list allcomponents which has no content submitted in the POST
        if not activity.group:
            new_sub = StudentSubmission()   # the submission foreign key for newly submitted components
            new_sub.member = get_object_or_404(Member, offering__slug=course_slug, person__userid=request.user.username)
        elif gm:
            new_sub = GroupSubmission()
            new_sub.group = group
            new_sub.creator = member
        else:
            messages.add_message(request, messages.ERROR, "This is a group submission. You cannot submit since you aren't in a group.")
            return ForbiddenResponse(request)
        new_sub.activity = activity

        # begin validating uploaded data
        submitted_comp = []
        not_submitted_comp = []
        # validate forms one by one
        for data in component_form_list:
            component = data['comp']
            form = data['form']
            if form.is_valid():
                sub = form.save(commit=False)
                sub.component = component
                submitted_comp.append(sub)
            else:
                # hack to replace the "required" message to something more appropriate
                for k,v in form.errors.items():
                    for i,e in enumerate(v):
                        if e == "This field is required.":
                            v[i] = "Nothing submitted."

                not_submitted_comp.append(component)
        # check duplicate filenames here
        all_ok = False
        while not all_ok:
            all_ok = True
            d = {}
            for c,s in submitted_components:
                d[c] = s and s.get_filename()
            for s in submitted_comp:
                d[s.component] = s.get_filename()
            # a list holding all file names
            file_name_list = [a[1] for a in d.items() if a[1] is not None]
            to_be_removed = []
            for (i, s) in enumerate(submitted_comp):
                if file_name_list.count(s.get_filename()) > 1:
                    all_ok = False
                    to_be_removed.append(i)
                    not_submitted_comp.append(s.component)
                    #HACK: modify the 'errors' field in the form
                    for data in component_form_list:
                        if s.component == data['comp']:
                            # assume we have only one field for submission form
                            field_name = data['form'].fields.keys()[0]
                            data['form']._errors[field_name] = ErrorList([u"This file has the same name as another file in your submission."])
            # remove those has errors in submitted_comp
            to_be_removed.reverse()
            for t in to_be_removed:
                submitted_comp.pop(t)
        # all okay now
        # end validating, begin saving
        if len(submitted_comp) > 0:
            new_sub.save()    
        for sub in submitted_comp:
            sub.submission = new_sub
            sub.save()
            #LOG EVENT#
            if activity.group:
                group_str = " as a member of group %s" % new_sub.group.name
            else:
                group_str = ""
            l = LogEntry(userid=request.user.username,
                  description=u"submitted for %s %s%s" % (activity, sub.component.title, group_str),
                  related_object=sub)
            l.save()

        if len(not_submitted_comp) == 0:
            messages.add_message(request, messages.SUCCESS, "Your submission was successful.")
            return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))

        return render(request, "submission/submission_error.html",
            {"course":course, "activity":activity, "component_list":component_form_list,
            "submitted_comp":submitted_comp, "not_submitted_comp":not_submitted_comp})
    else: #not POST
        if activity.group and gm:
            messages.add_message(request, messages.INFO, "This is a group submission. You will submit on behalf of the group %s." % group.name)
        
        component_form_list = make_form_from_list(component_list)
        return render(request, "submission/" + template,
        {'component_form_list': component_form_list, "course": course, "activity": activity, "submission": submission,
         "submitted_components":submitted_components, "userid":userid, "late":late, "student":student, "group":group,
         "cansubmit":cansubmit, "is_staff":staff})

@requires_course_by_slug
def show_components_submission_history(request, course_slug, activity_slug, userid=None):
    if userid is None:
        userid = request.GET.get('userid')
    course = get_object_or_404(CourseOffering, slug = course_slug)
    activity = get_object_or_404(course.activity_set,slug = activity_slug, deleted=False)
    staff = False

    if userid is None:
        # can always see your own submissions
        userid = request.user.username
    else:
        # specifying a userid: must be course staff
        if is_course_staff_by_slug(request, course.slug):
            staff = True
        else:
            return ForbiddenResponse(request)

    if activity.group:
        messages.add_message(request, messages.INFO, "This is a group submission. This history is based on submissions from all your group members.")
        gms = GroupMember.objects.filter(student__person__userid=userid, confirmed=True, activity=activity)
        submissions = GroupSubmission.objects.filter(activity=activity, group__groupmember__in=gms)
    else:
        submissions = StudentSubmission.objects.filter(activity=activity, member__person__userid=userid)

    # get all submission components
    component_list = select_all_components(activity, include_deleted=staff)
    all_submitted_components = []
    for submission in submissions:
        c = get_submission_components(submission, activity, component_list)
        all_submitted_components.append({'sub':submission, 'comp':c})
    
    return render(request, "submission/submission_history_view.html",
        {"course":course, "activity":activity,'userid':userid,'submitted_components': all_submitted_components})

#staff submission configuratiton
def _show_components_staff(request, course_slug, activity_slug):
    """
    Show all the components of this activity
    Responsible for updating position
    """
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug=activity_slug, deleted=False)

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
    return render(request, "submission/component_view_staff.html",
        {"course":course, "activity":activity, "component_list":component_list})



@requires_course_staff_by_slug
def edit_single(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug=activity_slug, deleted=False)
    component_list = select_all_components(activity)

    #get component
    edit_id = request.GET.get('id')
    component = get_component(activity=activity, id=edit_id)
    if component is None:
        return NotFoundResponse(request)

    form = component.Type.ComponentForm(instance=component)
                
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
                  description=(u"edited component %s of %s") % (component.title, activity),
                  related_object=new_component)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'Component "' + new_component.title + '" successfully updated.')
            return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))
        else:
            form = new_form
            messages.add_message(request, messages.ERROR, 'Please correct the errors in the form.')

    return render(request, "submission/component_edit_single.html",
            {"course":course, "activity":activity, "component":component, "edit_id":edit_id, "form":form})

@requires_course_staff_by_slug
def add_component(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug, deleted=False)

    #default, Archive
    typelabel = request.GET.get('type')
    Type = find_type_by_label(typelabel)
    
    if Type is None:
        form = None
    else:
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
                  description=(u"added %s component %s for %s") % (Type.name, new_component.title, activity),
                  related_object=new_component)
            l.save()
            messages.add_message(request, messages.SUCCESS, 'New component "' + new_component.title + '" successfully added.')
            return HttpResponseRedirect(reverse(show_components, args=[course_slug, activity_slug]))
        else:
            messages.add_message(request, messages.ERROR, 'Please correct the errors in the form.')
            form = new_form

    type_classes = ALL_TYPE_CLASSES
    return render(request, "submission/component_add.html",
        {"course":course, "activity":activity, "form":form, "type":Type, "types": type_classes})

def get_submission(submission_id):
    try:
        return StudentSubmission.objects.get(id=submission_id)
    except StudentSubmission.DoesNotExist:
        try:
            return GroupSubmission.objects.get(id=submission_id)
        except GroupSubmission.DoesNotExist:
            return None
    


@requires_course_by_slug
@uses_feature('submit-get')
def download_file(request, course_slug, activity_slug, component_slug=None, submission_id=None, userid=None):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug = activity_slug, deleted=False)
    staff = False
    if is_course_staff_by_slug(request, course_slug):
        staff = True
    
    # find the appropriate submission object
    if submission_id:
        # explicit request: get that one.
        submission = get_submission(submission_id)
        if not submission or submission.activity!=activity:
            return NotFoundResponse(request)
        submitted_components = get_submission_components(submission, activity, include_deleted=staff)

    elif userid:
        # userid specified: get their most recent submission
        student = get_object_or_404(Person, userid=userid)
        submission, submitted_components = get_current_submission(student, activity, include_deleted=staff)
        if not submission:
            return NotFoundResponse(request)
    
    else:
        return NotFoundResponse(request)

    
    # make sure this user is allowed to see the file
    if staff:
        pass
    elif isinstance(submission, GroupSubmission):
        membership = submission.group.groupmember_set.filter(student__person__userid=request.user.username, activity=activity, confirmed=True)
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

@requires_course_staff_by_slug
@uses_feature('submit-get')
def download_activity_files(request, course_slug, activity_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug=activity_slug, deleted=False)

    return generate_activity_zip(activity)

@requires_course_staff_by_slug
def show_student_submission_staff(request, course_slug, activity_slug, userid):
    return _show_components_student(request, course_slug, activity_slug, userid, "view_student_dashboard_staff.html", staff=True)

@requires_course_staff_by_slug
def show_student_history_staff(request, course_slug, activity_slug, userid):
    return show_components_submission_history(request, course_slug, activity_slug, userid)

@requires_course_staff_by_slug
def take_ownership_and_mark(request, course_slug, activity_slug, userid=None, group_slug=None):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    activity = get_object_or_404(course.activity_set, slug=activity_slug, deleted=False)

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
            else:
                submission = StudentSubmission.objects.filter(activity=activity, member__person__userid=userid).latest('created_at')
        except:
            submission = None
        response = HttpResponseRedirect(reverse(marking_student, args=[course_slug, activity_slug, userid]) + urlencode)
        #if it is taken by someone not me, show a confirm dialog
        if request.GET.get('confirm') == None:
            # check disabled until such time as it can be fixed
            if False and submission and submission.owner and submission.owner.person.userid != request.user.username:
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
              description=(u"took ownership on %s" + str + " by %s") % (activity, userid),
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
            # check disabled until such time as it can be fixed
            if False and submission and submission.owner and submission.owner.person.userid != request.user.username:
                return _override_ownership_confirm(request, course, activity, None, group_slug, submission.owner.person, urlencode[1:])

        if submission:
            submission.set_owner(course, request.user.username)
        #LOG EVENT#
        groups = Group.objects.all().filter(courseoffering=course)
        group = get_object_or_404(groups, slug=group_slug)
        if submission:
            str = (" of submission %i by group %s") % (submission.id, submission.file_slug())
        else:
            str = ""
        l = LogEntry(userid=request.user.username,
          description=(u"took ownership on %s"+str+ " by group %s") % (activity, group.name),
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
        
    
    return render(request, "submission/override_ownership_confirm.html",
        {"course":course, "activity":activity, "student":student, "group":group, "old_owner":old_owner, "true":True,
         "urlencode":urlencode, "userid":userid})
