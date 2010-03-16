# Create your views here.
from django.contrib.auth.decorators import login_required
from coredata.models import Member, Person, CourseOffering
from groups.models import *
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from groups.forms import GroupForm
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from contrib import messages
from courselib.auth import requires_course_by_slug, requires_course_staff_by_slug, is_course_staff_by_slug, is_course_student_by_slug

#@login_required
#def index(request):
#    p = get_object_or_404(Person, userid = request.user.username)
#    courselist = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person = p)\
#               .select_related('offering','offering__semester')
#    return render_to_response('groups/index.html', {'courselist':courselist}, context_instance = RequestContext(request))

@login_required
def groupmanage(request, course_slug):
    #course = CourseOffering.objects.get(slug=course_slug)
    #p = get_object_or_404(Person, userid = request.user.username)
    #m = get_object_or_404(Member, person = p, offering=course)
    #try:
    #    grouplist = Group.objects.filter(courseoffering = course)
    #except:
    #    grouplist = None
    #memberlist = GroupMember.objects.none()
    if is_course_student_by_slug(request.user, course_slug):
        #gs = Group.objects.filter(courseoffering=course, groupmember__student=m)
        #g = None
        #if gs is not None:
        #    try:
        #        g = gs.get(confirmed=True)
        #    except:
        #        g = None
        #if g is not None:
        #    memberlist = GroupMember.objects.filter(group = g)
        #else:
        #    memberlist = None
        return _groupmanage_student(request, course_slug)
    elif is_course_staff_by_slug(request.user, course_slug):
        return render_to_response('groups/instructor.html', {'course_slug':course_slug, 'grouplist':grouplist}, context_instance = RequestContext(request))
    else:
        return HttpResponseForbidden()


def _groupmanage_student(request, course_slug):
    course = get_object_or_404(CourseOffering, slug=course_slug)
    members = GroupMember.objects.filter(group__courseoffering=course, student__person__userid=request.user.username)
    
    print members
    
    return render_to_response('groups/student.html', {'course':course, 'members':members}, context_instance = RequestContext(request))

@requires_course_by_slug
def create(request,course_slug):
    p = get_object_or_404(Person,userid=request.user.username)
    c = get_object_or_404(CourseOffering, slug = course_slug)
    group_manager=Member.objects.get(person = p, offering = c)
    return render_to_response('groups/create.html', {'manager':group_manager, 'course':c},context_instance = RequestContext(request)) 

@requires_course_by_slug
def submit(request,course_slug):
    p = get_object_or_404(Person,userid=request.user.username)
    c = get_object_or_404(CourseOffering, slug = course_slug)
    m = Member.objects.get(person = p, offering = c)
    name = request.POST['GroupName']
    g = Group(name = name, manager = m, courseoffering=c)
    g.save()
    
    gm = GroupMember(group=g, student=m, confirmed=True)
    gm.save()
    
    messages.add_message(request, messages.SUCCESS, 'Group Created')
    return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))

@requires_course_by_slug
def join(request, course_slug, group_slug):
    c = get_object_or_404(CourseOffering, slug=course_slug)
    g = get_object_or_404(Group, courseoffering = c, slug = group_slug)
    p = get_object_or_404(Person, userid = request.user.username)
    m = get_object_or_404(Member, person = p, offering=c)
    gm = get_object_or_404(GroupMember, group=g, student=m)
    gm.confirmed = True
    gm.save();
    
    messages.add_message(request, messages.SUCCESS, 'You have joined the group "%s".' % (g.name))
    return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))

@requires_course_by_slug
def invite(request, course_slug, group_slug):
    course = get_object_or_404(CourseOffering, slug = course_slug)
    group = get_object_or_404(Group, courseoffering = course, slug = group_slug)
    
    students_qset = course.members.filter(person__role = 'STUD')   
    from django import forms 
    class StudentReceiverForm(forms.Form):
        student = forms.ModelChoiceField(queryset = students_qset) 
        
    if request.method == "POST": 
        student_receiver_form = StudentReceiverForm(request.POST)
        if student_receiver_form.is_valid():
            student = student_receiver_form.cleaned_data["student"]
            print student
            member = Member.objects.get(person = student, offering = course)
            groupMember = GroupMember(group = group, student = member, confirmed = False) 
            groupMember.save()
            
            messages.add_message(request, messages.SUCCESS, 'Your invitation to "%s" has been sent out.' % (student))
            return HttpResponseRedirect(reverse('groups.views.groupmanage', kwargs={'course_slug': course_slug}))
    else:
        student_receiver_form = StudentReceiverForm()
        return render_to_response("groups/invite.html", {'student_receiver_form': student_receiver_form}, context_instance=RequestContext(request))
                                  

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
