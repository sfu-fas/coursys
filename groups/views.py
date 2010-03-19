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
    
    return render_to_response('groups/instructor.html', {'course':course, 'members':members}, context_instance = RequestContext(request))

@requires_course_by_slug
def create(request,course_slug):
    person = get_object_or_404(Person,userid=request.user.username)
    course = get_object_or_404(CourseOffering, slug = course_slug)
    group_manager=Member.objects.get(person = person, offering = course)
    
    #TODO can instructor create group based on unreleased activities?
    #TODO need to make the form of activities uneditable
    activities = Activity.objects.filter(offering = course, status = 'RLS')
    #activities = Activity.objects.filter(offering = course)
    initialData = []
    for i in range(len(activities)):
        activity = dict(selected = False, name = activities[i].name, \
                        percent = activities[i].percent, due_date = activities[i].due_date)
        print "act: %s", activity
        initialData.append(activity)
        
    Formset = formset_factory(ActivityForm, extra = 0)
    formset = Formset(initial = initialData)
    
    return render_to_response('groups/create.html', {'manager':group_manager, 'course':course, 'formset':formset},context_instance = RequestContext(request)) 

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
    ActivityFormset = formset_factory(ActivityForm)
    formset = ActivityFormset(request.POST)
    
    if formset.is_valid():      
        print formset.cleaned_data
        for i in range(len(formset.cleaned_data)):
            if formset.cleaned_data[i]['selected'] == True:
                activity = Activity.objects.get(offering = course, name = formset.cleaned_data[i]['name'])
                groupMember = GroupMember(group=group, student=member, confirmed=True, activity = activity)
                groupMember.save()
    
    messages.add_message(request, messages.SUCCESS, 'Group Created')
    return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))

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
