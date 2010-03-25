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
    
    return render_to_response('groups/student.html', {'course':course, 'members':members}, context_instance = RequestContext(request))

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
    
    return render_to_response('groups/instructor.html', \
                              {'course':course, 'members':members, 'studentsNotInGroup':studentsNotInGroup}, \
                              context_instance = RequestContext(request))

@requires_course_by_slug
def create(request,course_slug):
    person = get_object_or_404(Person,userid=request.user.username)
    course = get_object_or_404(CourseOffering, slug = course_slug)
    group_manager=Member.objects.get(person = person, offering = course)
    
    #TODO can instructor create group based on unreleased activities?
    activities = Activity.objects.filter(offering = course, status = 'URLS') 
    activityList = []
    for activity in activities:
        activityForm = ActivityForm(prefix = activity.slug)
        print "act:", activity
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
    #TODO: validate group name and activity
    person = get_object_or_404(Person,userid=request.user.username)
    course = get_object_or_404(CourseOffering, slug = course_slug)
    member = Member.objects.get(person = person, offering = course)
    name = request.POST['GroupName']
    group = Group(name = name, manager = member, courseoffering=course)
    group.save()
    
    #Deal with creating the membership
    if is_course_student_by_slug(request.user, course_slug):
        activities = Activity.objects.filter(offering = course, status = 'URLS') 
        for activity in activities:
            activityForm = ActivityForm(request.POST, prefix = activity.slug)
            if activityForm.is_valid() and activityForm.cleaned_data['selected'] == True:
                groupMember = GroupMember(group=group, student=member, confirmed=True, activity = activity)
                groupMember.save()        
    
        messages.add_message(request, messages.SUCCESS, 'Group Created')
        return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))
    
    elif is_course_staff_by_slug(request.user, course_slug):
        activities = Activity.objects.filter(offering = course, status = 'URLS') 
        students = Member.objects.select_related('person').filter(offering = course, role = 'STUD')  

        for activity in activities:
            activityForm = ActivityForm(request.POST, prefix = activity.slug)
            if activityForm.is_valid() and activityForm.cleaned_data['selected'] == True:
                for student in students:
                    studentForm = StudentForm(request.POST, prefix = student.person.userid)
                    if studentForm.is_valid() and studentForm.cleaned_data['selected'] == True:
                        groupMember = GroupMember(group=group, student=student, confirmed=True, activity = activity)
                        groupMember.save()
                    
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
            member = Member.objects.get(person = newPerson, offering = course)
            if GroupMember.objects.filter(student=member,group=group):
                error_info="Student %s has already exists" % (newPerson)
            else:
                #member = Member.objects.get(person = newPerson, offering = course)
                for invitorMembership in GroupMember.objects.filter(group = group, student = invitor):
                    newGroupMember = GroupMember(group = group, student = member, \
                                          activity = invitorMembership.activity, confirmed = False)
                    newGroupMember.save()

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
def delete_group(request, course_slug, group_slug):   
    course = get_object_or_404(CourseOffering, slug = course_slug)
    group = get_object_or_404(Group, courseoffering = course, slug = group_slug)
    if request.method == "POST": 
        groupMembers = GroupMember.objects.filter(group=group)
        groupMembers.delete()
        group.delete()
        return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))
        
    else:
        return render_to_response("groups/delete.html", {'course' : course, 'group' : group}, \
                              context_instance=RequestContext(request))
    
@requires_course_by_slug
def change_name(request, course_slug, group_slug):   
    #Change the group's name
    course = get_object_or_404(CourseOffering, slug = course_slug)
    group = get_object_or_404(Group, courseoffering = course, slug = group_slug)
    if request.method == "POST": 
        groupForm = GroupForm(request.POST)
        if groupForm.is_valid():
            group.name = groupForm.cleaned_data['name']
            group.save()
        return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))
        
    else:
        groupForm = GroupForm(instance = group)
        return render_to_response("groups/change_name.html", \
                                  {'groupForm' : groupForm, 'course' : course, 'group' : group}, \
                                  context_instance=RequestContext(request))
                                  

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
