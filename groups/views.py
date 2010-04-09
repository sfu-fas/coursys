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
from courselib.auth import requires_course_by_slug, requires_course_staff_by_slug, is_course_staff_by_slug, is_course_student_by_slug
from log.models import *


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
    #NoDuplicateMembers=set(members)  
    #activities = Activity.objects.filter(offering = course, status = 'RLS') 
    #students = Member.objects.select_related('person').filter(offering = course, role = 'STUD')
    #groups= Group.objects.filter(courseoffering=course)
    #plist= []
    #groupmember=GroupMember.objects.filter(student__person__userid=request.user.username)
    groups=Group.objects.filter(groupmember__student__person__userid=request.user.username)
    #NoDuplicateGroups=list(Set(groups))
    membersNotInDuplicateGroup = [] 
    membersInDuplicateGroup = []
    NoDuplicateGroupmembers=[]
    #countGroup=0;
    for member in members:
        counter=0
        memberNotInDuplicateGroupFlag=True
        for group in groups:
            if member.group == group:
                counter=counter+1
                if counter>1:
                    memberNotInDuplicateGroupFlag=False
        if memberNotInDuplicateGroupFlag==True:
            membersNotInDuplicateGroup.append(member)
        else:
            membersInDuplicateGroup.append(member)
            
    for member in membersInDuplicateGroup:
        memberone=member
        counter=0
        for member in membersInDuplicateGroup:
            if memberone.group==member.group:
                counter=counter+1
                if counter>1:
                    membersInDuplicateGroup.remove(member)
    
    for member in membersInDuplicateGroup:
        memberone=member
        counter=0
        for member in membersInDuplicateGroup:
            if memberone.student==member.student:
                if memberone.group==member.group:
                    counter=counter+1
            if counter>1:
                    membersInDuplicateGroup.remove(member)
    
    for member in membersInDuplicateGroup:
        membersNotInDuplicateGroup.append(member)
     
    return render_to_response('groups/student.html', {'course':course, 'groups':groups,'members':membersNotInDuplicateGroup}, context_instance = RequestContext(request))

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
        if members:
            #get the members for the group
            memberships = GroupMember.objects.filter(group = group, activity = members[0].activity)
            confirmedStudents = []
            unconfirmedStudents = []
            for membership in memberships:
                if membership.confirmed == True:
                    confirmedStudents.append(membership)
                else:
                    unconfirmedStudents.append(membership)
            #get the activities for the group
            memberships = GroupMember.objects.filter(group = group, student = members[0].student)
            activities = []
            for membership in memberships:
                activities.append(membership.activity)
            #create a dictionary structure that contains the info of group members and activities of the group
            groupDict = {'group':group, 'activities':activities, 'confirmedStudents':confirmedStudents, 'unconfirmedStudents':unconfirmedStudents}
            groupList.append(groupDict)
            #print groupDict
    #print groupList
    print groupList[0]['confirmedStudents']
                
    return render_to_response('groups/instructor.html', \
                              {'course':course, 'groupList':groupList, 'studentsNotInGroup':studentsNotInGroup}, \
                              context_instance = RequestContext(request))

@requires_course_by_slug
def create(request,course_slug):
    person = get_object_or_404(Person,userid=request.user.username)
    course = get_object_or_404(CourseOffering, slug = course_slug)
    group_manager=Member.objects.get(person = person, offering = course)
    #TODO can instructor create group based on unreleased activities?
    activities = Activity.objects.filter(offering = course, status = 'RLS', group=True) 
    activityList = []
    for activity in activities:
        activityForm = ActivityForm(prefix = activity.slug)
        activityList.append({'activityForm': activityForm, 'name' : activity.name,\
                             'percent' : activity.percent, 'due_date' : activity.due_date})

    if is_course_student_by_slug(request.user, course_slug):
        return render_to_response('groups/create_student.html', \
                                  {'manager':group_manager, 'course':course, 'activityList':activityList},\
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
                          {'manager':group_manager, 'course':course, 'activityList':activityList, \
                           'studentList':studentList}, context_instance = RequestContext(request))
    else:
        return HttpResponseForbidden()    
    
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
        if is_course_student_by_slug(request.user, course_slug):
            return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))
        elif is_course_staff_by_slug(request.user, course_slug):
            return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))   
        

    else:
        group = Group(name = name, manager = member, courseoffering=course)
        group.save()
        #LOG EVENT#
        l = LogEntry(userid=request.user.username,
        description="created a new group %s for %s." % (group.name, course),
        related_object=group )
        l.save()
        #Deal with creating the membership
        if is_course_student_by_slug(request.user, course_slug):
            activities = Activity.objects.filter(offering = course, status = 'RLS') 
            for activity in activities:
                activityForm = ActivityForm(request.POST, prefix = activity.slug)
                if activityForm.is_valid() and activityForm.cleaned_data['selected'] == True:
                    groupMember = GroupMember(group=group, student=member, confirmed=True, activity = activity)
                    groupMember.save()
                    #LOG EVENT#
                    l = LogEntry(userid=request.user.username,
                    description="automatically became a group member of %s for activity %s." % (group.name, groupMember.activity),
                    related_object=groupMember )
                    l.save()

            messages.add_message(request, messages.SUCCESS, 'Group Created')
            return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))    
        elif is_course_staff_by_slug(request.user, course_slug):
            activities = Activity.objects.filter(offering = course, status = 'RLS') 
            students = Member.objects.select_related('person').filter(offering = course, role = 'STUD') 
            for activity in activities:
                activityForm = ActivityForm(request.POST, prefix = activity.slug)
                if activityForm.is_valid() and activityForm.cleaned_data['selected'] == True:
                    for student in students:
                        studentForm = StudentForm(request.POST, prefix = student.person.userid)
                        if studentForm.is_valid() and studentForm.cleaned_data['selected'] == True:
                            groupMember = GroupMember(group=group, student=student, confirmed=True, activity = activity)
                            groupMember.save()
                        #LOG EVENT#
                            l = LogEntry(userid=request.user.username,
                            description="added %s as a group member to %s for activity %s." % (student.person.userid,group.name, groupMember.activity),
                            related_object=groupMember )
                            l.save()                    
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
    description="joined group %s for activity %s." % (group.name, groupMember.activity),
    related_object=groupMember )
    l.save()
    messages.add_message(request, messages.SUCCESS, 'You have joined the group "%s".' % (group.name))
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
            if GroupMember.objects.filter(student=member,group=group):
                error_info="Student %s has already exists" % (newPerson)
            else:
                #member = Member.objects.get(person = newPerson, offering = course)
                for invitorMembership in GroupMember.objects.filter(group = group, student = invitor):
                    newGroupMember = GroupMember(group = group, student = member, \
                                          activity = invitorMembership.activity, confirmed = False)
                    newGroupMember.save()
                    #LOG EVENT#
                    l = LogEntry(userid=request.user.username,
                    description="invited %s to join group %s for activity %s." % (newGroupMember.student.person.userid,group.name, newGroupMember.activity),
                    related_object=newGroupMember )
                    l.save()

            if error_info:
                messages.add_message(request, messages.ERROR, error_info)
            else:
                messages.add_message(request, messages.SUCCESS, 'Your invitation to "%s" has been sent out.' % (newPerson))
            return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))
    else:
        student_receiver_form = StudentReceiverForm()
        context = {'course': course, 'form': student_receiver_form}
        return render_to_response("groups/invite.html", context, context_instance=RequestContext(request))

@requires_course_by_slug
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
        students = GroupMember.objects.filter(group = group)
        #if there is not member in this group, delete the group
        if not students:
            group.delete()
            #LOG EVENT#
            l = LogEntry(userid=request.user.username,
            description="deleted group %s for course %s." % (group.name, group.courseoffering),
            related_object=group)
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
    
@requires_course_by_slug
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
        return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))
        
    else:
        groupForm = GroupForm(instance = group)
        return render_to_response("groups/change_name.html", \
                                  {'groupForm' : groupForm, 'course' : course, 'group' : group}, \
                                  context_instance=RequestContext(request))
    
@requires_course_by_slug
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

@requires_course_by_slug
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
