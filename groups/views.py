# Create your views here.
from django.contrib.auth.decorators import login_required
from coredata.models import Member, Person, CourseOffering
from groups.models import *
from grades.models import Activity
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from groups.forms import *
from django.forms.models import modelformset_factory
from django.forms.formsets import formset_factory
from django.forms.util import ErrorList
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from contrib import messages
from django.conf import settings
from courselib.auth import *
from log.models import *
from django.db.models import Q

#@login_required
#def index(request):
#    p = get_object_or_404(Person, userid = request.user.username)
#    courselist = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person = p)\
#               .select_related('offering','offering__semester')
#    return render_to_response('groups/index.html', {'courselist':courselist}, context_instance = RequestContext(request))

@login_required
def groupmanage(request, course_slug):
    if is_course_student_by_slug(request.user, course_slug):
        return _groupmanage_student(request, course_slug)
    elif is_course_staff_by_slug(request.user, course_slug):
        return _groupmanage_staff(request, course_slug)
    else:
        return HttpResponseForbidden()

def _groupmanage_student(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    members = GroupMember.objects.filter(group__courseoffering=course, student__person__userid=request.user.username)

    groups = Group.objects.filter(courseoffering=course, groupmember__student__person__userid=request.user.username)
    groups = set(groups) # all groups student is a member of

    groupList = []
    my_membership = []
    for group in groups:
        members = GroupMember.objects.filter(group = group)
        need_conf = members.filter(student__person__userid=request.user.username, confirmed=False).count() != 0
        all_act = all_activities(members)
        unique_members = []
        for s in set(m.student for m in members):
            # confirmed in group?
            confirmed = False not in (m.confirmed for m in members if m.student==s)
            # not a member for any activities?
            missing = all_act - set(m.activity for m in members if m.student==s)
            unique_members.append( {'member': s, 'confirmed': confirmed, 'missing': missing} )

        groupList.append({'group': group, 'activities': all_act, 'unique_members': unique_members, 'memb': members, 'need_conf': need_conf})

    return render_to_response('groups/student.html', {'course':course, 'groupList':groupList}, context_instance = RequestContext(request))

def _groupmanage_staff(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    members = GroupMember.objects.filter(group__courseoffering=course)
    #find the students not in any group
    students = Member.objects.select_related('person').filter(offering = course, role = 'STUD')
    studentsNotInGroup = []
    for student in students:
        studentNotInGroupFlag = True
        for groupMember in members:
            if student == groupMember.student:
                studentNotInGroupFlag = False
        if studentNotInGroupFlag == True:
            studentsNotInGroup.append(student)

    groups = Group.objects.filter(courseoffering = course)
    groupList = []
    for group in groups:
        members = GroupMember.objects.filter(group = group)
        all_act = all_activities(members)
        unique_members = []
        for s in set(m.student for m in members):
            # confirmed in group?
            confirmed = False not in (m.confirmed for m in members if m.student==s)
            # not a member for any activities?
            missing = all_act - set(m.activity for m in members if m.student==s)
            unique_members.append( {'member': s, 'confirmed': confirmed, 'missing': missing} )
        groupList.append({'group': group, 'activities': all_act, 'unique_members': unique_members, 'memb': members})

    return render_to_response('groups/instructor.html', \
                              {'course':course, 'groupList':groupList, 'studentsNotInGroup':studentsNotInGroup}, \
                              context_instance = RequestContext(request))

@requires_course_by_slug
def create(request,course_slug):
    person = get_object_or_404(Person,userid=request.user.username)
    course = get_object_or_404(CourseOffering, slug = course_slug)
    group_manager=Member.objects.get(person = person, offering = course)
    groupForSemesterForm = GroupForSemesterForm()
    activities = Activity.objects.exclude(status='INVI').filter(offering=course, group=True)
    activityList = []
    for activity in activities:
        activityForm = ActivityForm(prefix = activity.slug)
        activityList.append({'activityForm': activityForm, 'name' : activity.name,\
                             'percent' : activity.percent, 'due_date' : activity.due_date})

    if is_course_student_by_slug(request.user, course_slug):
        return render_to_response('groups/create_student.html', \
                                  {'manager':group_manager, 'course':course, 'groupForSemester':groupForSemesterForm, 'activityList':activityList},\
                                  context_instance = RequestContext(request))

    elif is_course_staff_by_slug(request.user, course_slug):
        #For instructor page, there is a student table for him/her to choose the students who belong to the new group
        students = Member.objects.select_related('person').filter(offering = course, role = 'STUD')
        studentList = []
        for student in students:
            studentForm = StudentForm(prefix = student.person.userid)
            studentList.append({'studentForm': studentForm, 'first_name' : student.person.first_name,\
                                 'last_name' : student.person.last_name, 'userid' : student.person.userid,\
                                 'emplid' : student.person.emplid})

        return render_to_response('groups/create_instructor.html', \
                          {'manager':group_manager, 'course':course,'groupForSemester':groupForSemesterForm, 'activityList':activityList, \
                           'studentList':studentList}, context_instance = RequestContext(request))
    else:
        return HttpResponseForbidden()
    
def validateIntegrity(request, isStudentCreatedGroup, groupForSemester, course, studentList, activityList):
    """
    #If one student is in a group for an activity, he/she cannot be in another group for the same activity.
    """
    integrityError = False
    error_info = ""
    print activityList
    for student in studentList:
        groupMembers = GroupMember.objects.filter(group__courseoffering = course, student = student)
        #check if the student is already in a group for all group activities of the semester
        for group in set(groupMember.group for groupMember in groupMembers):
            if groupForSemester == True and group.groupForSemester == True:
                integrityError = True
                #if this group is created by student
                if isStudentCreatedGroup:
                    error_info = error_info + "You can not create this group, \
                    because you are already in the group: %s for all activities of the semester" % (group.name)
                #if this group is created by instructor 
                else: 
                    error_info = error_info + "Student %s %s (%s)can not be assigned to this new group,\
                    because he/she is already in group %s for all activities of the semester.\n" \
                               % (student.person.first_name, student.person.last_name, student.person.userid, group.name)
        if integrityError == True:
            continue
        #check if the student is in a group that already has one or more than one activities in the activityList
        for activity in activityList:
            for groupMember in groupMembers:
                if groupMember.activity == activity:
                    integrityError = True
                    #if this group is created by student
                    if isStudentCreatedGroup:
                        error_info = error_info + "You can not create this group for %s, \
                        because you are already in the group: %s for %s.\n"\
                                   % (activity.name, groupMember.group.name, activity.name)
                    #if this group is created by instructor 
                    else: 
                        error_info = error_info + "Student %s %s (%s)can not be assigned to this new group for %s,\
                        because he/she is already in group %s for %s.\n" \
                                   % (student.person.first_name, student.person.last_name, student.person.userid,\
                                    activity.name, groupMember.group.name, activity.name)
    messages.add_message(request, messages.ERROR, error_info)
    return not integrityError

@requires_course_by_slug
def submit(request,course_slug):
    #TODO: validate activity?
    person = get_object_or_404(Person,userid=request.user.username)
    course = get_object_or_404(CourseOffering, slug = course_slug)
    member = Member.objects.get(person = person, offering = course)
    error_info=None
    name = request.POST.get('GroupName')
    #Check if group has a unique name
    if Group.objects.filter(name=name,courseoffering=course):
        error_info="Group %s has already exists" % (name)
        messages.add_message(request, messages.ERROR, error_info)
        return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))
    #Check if the group name is empty, these two checks may need to be moved to forms later.
    if name == "":
        error_info = "Group name cannot be empty, pleaes input a group name"
        messages.add_message(request, messages.ERROR, error_info)
        return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))
    

    else:
        # find selected activities
        selected_act = []
        activities = Activity.objects.filter(offering=course, group=True)
        if not is_course_staff_by_slug(request.user, course_slug):
            activities = activities.exclude(status='INVI')

        for activity in activities:
            activityForm = ActivityForm(request.POST, prefix=activity.slug)
            if activityForm.is_valid() and activityForm.cleaned_data['selected'] == True:
                selected_act.append(activity)
        
        # no selected activities: fail.
        if not selected_act:
            messages.add_message(request, messages.ERROR, "Group not created: no activities selected.")
            return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))
        
        groupForSemesterForm = GroupForSemesterForm(request.POST)
        if groupForSemesterForm.is_valid():
            groupForSemester = groupForSemesterForm.cleaned_data['selected']
        
        #validate database integrity before saving anything. 
        #If one student is in a group for an activity, he/she cannot be in another group for the same activity.
        if is_course_student_by_slug(request.user, course_slug):
            isStudentCreatedGroup = True
            studentList = []
            studentList.append(member)
        elif is_course_staff_by_slug(request.user, course_slug):
            isStudentCreatedGroup = False
            studentList = []
            students = Member.objects.select_related('person').filter(offering = course, role = 'STUD')
            for student in students:
                studentForm = StudentForm(request.POST, prefix = student.person.userid)
                if studentForm.is_valid() and studentForm.cleaned_data['selected'] == True:
                    studentList.append(student)
        if validateIntegrity(request,isStudentCreatedGroup, groupForSemester, course, studentList, selected_act) == False:
            return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))
        
        group = Group(name=name, manager=member, courseoffering=course, groupForSemester = groupForSemester)
        group.save()
        #LOG EVENT#
        l = LogEntry(userid=request.user.username,
        description="created a new group %s for %s." % (group.name, course),
        related_object=group )
        l.save()

        if is_course_student_by_slug(request.user, course_slug):
            for activity in selected_act:
                groupMember = GroupMember(group=group, student=member, confirmed=True, activity=activity)
                groupMember.save()
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                description="automatically became a group member of %s for activity %s." % (group.name, groupMember.activity),
                    related_object=groupMember )
                l.save()

            messages.add_message(request, messages.SUCCESS, 'Group Created')
            return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))

        elif is_course_staff_by_slug(request.user, course_slug):
            students = Member.objects.select_related('person').filter(offering = course, role = 'STUD')
            for student in students:
                studentForm = StudentForm(request.POST, prefix = student.person.userid)
                if studentForm.is_valid() and studentForm.cleaned_data['selected'] == True:
                    for activity in selected_act:
                        groupMember = GroupMember(group=group, student=student, confirmed=True, activity=activity)
                        groupMember.save()
                        #LOG EVENT#
                        l = LogEntry(userid=request.user.username,
                        description="added %s as a group member to %s for activity %s." % (student.person.userid,group.name, groupMember.activity),
                            related_object=groupMember )
                        l.save()
                    
                    n = NewsItem(user=student.person, author=member.person, course=group.courseoffering,
                     source_app="group", title="Added to Group",
                     content="You have been added the group %s." % (group.name),
                     url=reverse('groups.views.groupmanage', kwargs={'course_slug':course.slug})
                    )
                    n.save()
                    
            messages.add_message(request, messages.SUCCESS, 'Group Created')
            return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))
        else:
            return HttpResponseForbidden()



@requires_course_by_slug
def join(request, course_slug, group_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    group = get_object_or_404(Group, courseoffering = course, slug = group_slug)
    person = get_object_or_404(Person, userid = request.user.username)
    member = get_object_or_404(Member, person = person, offering=course)

    for groupMember in GroupMember.objects.filter(group = group, student = member):
        groupMember.confirmed = True
        groupMember.save()

    #LOG EVENT#
    l = LogEntry(userid=request.user.username,
    description="joined group %s." % (group.name,),
    related_object=group )
    l.save()
    messages.add_message(request, messages.SUCCESS, 'You have joined the group "%s".' % (group.name))
    return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))

@requires_course_by_slug
def reject(request, course_slug, group_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    group = get_object_or_404(Group, courseoffering = course, slug = group_slug)
    person = get_object_or_404(Person, userid = request.user.username)
    member = get_object_or_404(Member, person = person, offering=course)

    # delete membership on reject
    GroupMember.objects.filter(group = group, student = member).delete()

    #LOG EVENT#
    l = LogEntry(userid=request.user.username,
    description="rejected membership in group %s." % (group.name,),
    related_object=group )
    l.save()
    messages.add_message(request, messages.SUCCESS, 'You have left the group "%s".' % (group.name))
    return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))

@requires_course_by_slug
def invite(request, course_slug, group_slug):
    #TODO need to validate the student who is invited, cannot be the invitor him/herself.
    course = get_object_or_404(CourseOffering, slug = course_slug)
    group = get_object_or_404(Group, courseoffering = course, slug = group_slug)
    person = get_object_or_404(Person, userid = request.user.username)
    invitor = get_object_or_404(Member, person = person, offering=course)
    error_info=None
    from django import forms
    class StudentReceiverForm(forms.Form):
        name = forms.CharField()

    if request.method == "POST":
        student_receiver_form = StudentReceiverForm(request.POST)
        #student_receiver_form.activate_addform_validation(course_slug,group_slug)
        if student_receiver_form.is_valid():
            name = student_receiver_form.cleaned_data['name']
            newPerson = get_object_or_404(Person, userid=name)
            member = get_object_or_404(Member, person = newPerson, offering = course, role="STUD")
            
            # find out if this person is already in a group
            gms = group.groupmember_set.all()
            all_act = all_activities(gms)
            existing_memb = GroupMember.objects.filter(student=member, activity__in=all_act)
            
            if GroupMember.objects.filter(student=member, group=group):
                error_info="%s is already in this group" % (newPerson.userid)
            elif existing_memb:
                error_info="%s is already in a group for %s" % (newPerson.userid, ", ".join(m.activity.name for m in existing_memb))
            else:
                #member = Member.objects.get(person = newPerson, offering = course)
                for invitorMembership in GroupMember.objects.filter(group = group, student = invitor):
                    newGroupMember = GroupMember(group = group, student = member, \
                                          activity = invitorMembership.activity, confirmed = False)
                    newGroupMember.save(member.person)

                    #LOG EVENT#
                    l = LogEntry(userid=request.user.username,
                    description="invited %s to join group %s for activity %s." % (newGroupMember.student.person.userid,group.name, newGroupMember.activity),
                    related_object=newGroupMember )
                    l.save()
                    
                n = NewsItem(user=member.person, author=person, course=group.courseoffering,
                     source_app="group", title="Group Invitation",
                     content="You have been invited to join group %s." % (group.name),
                     url=reverse('groups.views.groupmanage', kwargs={'course_slug':course.slug})
                    )
                n.save()

            if error_info:
                messages.add_message(request, messages.ERROR, error_info)
            else:
                messages.add_message(request, messages.SUCCESS, 'Your invitation to "%s" has been sent out.' % (newPerson))
            return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))
        else:
            messages.add_message(request, messages.ERROR, "Invalid userid.")
            return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))
    else:
        student_receiver_form = StudentReceiverForm()
        context = {'course': course, 'form': student_receiver_form}
        return render_to_response("groups/invite.html", context, context_instance=RequestContext(request))

@requires_course_staff_by_slug
def remove_student(request, course_slug, group_slug):
    course = get_object_or_404(CourseOffering, slug = course_slug)
    group = get_object_or_404(Group, courseoffering = course, slug = group_slug)
    students = GroupMember.objects.filter(group = group)

    if request.method == "POST":
        for student in students:
            studentForm = StudentForm(request.POST, prefix = student.student.person.userid)
            if studentForm.is_valid() and studentForm.cleaned_data['selected'] == True:
                student.delete()
                #LOG EVENT#
                l = LogEntry(userid=request.user.username,
                description="deleted %s in group %s for %s." % (student.student.person.userid,group.name,student.activity),
                related_object=student)
                l.save()
                #LOG EVENT#

        return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))

    else:
        studentList = []
        for student in students:
            studentForm = StudentForm(prefix = student.student.person.userid)
            studentList.append({'studentForm': studentForm, 'first_name' : student.student.person.first_name,\
                                 'last_name' : student.student.person.last_name, 'userid' : student.student.person.userid,\
                                 'emplid' : student.student.person.emplid})

        return render_to_response('groups/remove_student.html', \
                          {'course':course, 'group' : group, 'studentList':studentList}, \
                          context_instance = RequestContext(request))

@requires_course_staff_by_slug
def change_name(request, course_slug, group_slug):
    #Change the group's name
    course = get_object_or_404(CourseOffering, slug = course_slug)
    group = get_object_or_404(Group, courseoffering = course, slug = group_slug)
    if request.method == "POST":
        groupForm = GroupForm(request.POST)
        if groupForm.is_valid():
            oldname = group.name #used for log information
            group.name = groupForm.cleaned_data['name']
            group.save()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
            description="changed name of group %s to %s for course %s." % (oldname, group.name, group.courseoffering),
            related_object=group)
            l.save()
        else:
            messages.add_message(request, messages.ERROR, "New group name is not valid.")
        return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))

    else:
        groupForm = GroupForm(instance = group)
        return render_to_response("groups/change_name.html", \
                                  {'groupForm' : groupForm, 'course' : course, 'group' : group}, \
                                  context_instance=RequestContext(request))

@requires_course_staff_by_slug
def switch_group(request, course_slug, group_slug):
    #Change the group's name
    course = get_object_or_404(CourseOffering, slug = course_slug)
    group = get_object_or_404(Group, courseoffering = course, slug = group_slug)
    students = GroupMember.objects.filter(group = group)
    groupid = group.id
    group_qset = Group.objects.filter(courseoffering = course) \
        .select_related('courseoffering')

    from django import forms
    class StudentGroupForm(forms.Form):
        group = forms.ModelChoiceField(queryset = group_qset, initial = groupid)

    if request.method == "POST":
        for student in students:
            studentGroupForm = StudentGroupForm(request.POST, prefix = student.student.person.userid)
            print studentGroupForm.is_valid()
            if studentGroupForm.is_valid():
                student.group = studentGroupForm.cleaned_data['group']
                student.save()
        return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))

    else:
        studentList = []
        for student in students:
            studentGroupForm = StudentGroupForm(prefix = student.student.person.userid)
            studentList.append({'studentGroupForm': studentGroupForm, 'first_name' : student.student.person.first_name,\
                                 'last_name' : student.student.person.last_name, 'userid' : student.student.person.userid,\
                                 'emplid' : student.student.person.emplid})

        return render_to_response('groups/switch_group.html', \
                          {'course':course, 'group' : group, 'studentList':studentList}, \
                          context_instance = RequestContext(request))

@requires_course_staff_by_slug
def assign_student(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    members = GroupMember.objects.filter(group__courseoffering=course)

    #find the students not in any group
    students = Member.objects.select_related('person').filter(offering = course, role = 'STUD')
    studentsNotInGroup = []
    for student in students:
        studentNotInGroupFlag = True
        for groupMember in members:
            if student == groupMember.student:
                studentNotInGroupFlag = False
        if studentNotInGroupFlag == True:
            studentsNotInGroup.append(student)

    group_qset = Group.objects.filter(courseoffering = course) \
               .select_related('courseoffering')
    from django import forms
    class GroupForm(forms.Form):
        group = forms.ModelChoiceField(queryset = group_qset)

    if request.method == "POST":
        groupForm = GroupForm(request.POST)
        if groupForm.is_valid():
            group = groupForm.cleaned_data['group']

        #find the activities belong to this group
        groupMembers = GroupMember.objects.filter(group = group)
        if groupMembers:
            memberships = GroupMember.objects.filter(student = groupMembers[0].student)
            activityList = []
            for membership in memberships:
                activityList.append(membership.activity)

            #create new group member
            for activity in activityList:
                for student in studentsNotInGroup:
                    studentForm = StudentForm(request.POST, prefix = student.person.userid)
                    if studentForm.is_valid() and studentForm.cleaned_data['selected'] == True:
                        groupMember = GroupMember(group=group, student=student, confirmed=True, activity = activity)
                        groupMember.save()

        return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))

    else:
        groupForm = GroupForm()
        studentList = []
        for student in studentsNotInGroup:
            studentForm = StudentForm(prefix = student.person.userid)
            studentList.append({'studentForm': studentForm, 'first_name' : student.person.first_name,\
                                 'last_name' : student.person.last_name, 'userid' : student.person.userid,\
                                 'emplid' : student.person.emplid})

        return render_to_response('groups/assign_student.html', \
                          {'course':course, 'studentList':studentList, 'groupForm':groupForm}, \
                          context_instance = RequestContext(request))


#def joinconfirm(request):
#    return render_to_response('groups/create.html', context_instance = RequestContext(request))
#@requires_course_by_slug
#def invite(request, course_slug, group_slug):
    #p = get_object_or_404(Person,userid=request.user.username)
    #c = get_object_or_404(CourseOffering, slug = course_slug)
    #g = get_object_or_404(Group, courseoffering = c, slug = group_slug)
    #m = Member.objects.get(person = p, offering = c)
    #memberlist = GroupMember.objects.filter(group = g,student=m)
    #return render_to_response('groups/invite.html',context_instance = RequestContext(request))
