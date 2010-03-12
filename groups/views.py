# Create your views here.
from django.contrib.auth.decorators import login_required
from coredata.models import Member, Person, CourseOffering
from groups.models import *
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from groups.forms import GroupForm
from django.http import HttpResponse, HttpResponseRedirect

#@login_required
#def index(request):
#	p = get_object_or_404(Person, userid = request.user.username)
#	courselist = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person = p)\
#	           .select_related('offering','offering__semester')
#	return render_to_response('groups/index.html', {'courselist':courselist}, context_instance = RequestContext(request))

@login_required
def groupmanage(request, course_slug):
	course = CourseOffering.objects.get(slug=course_slug)
	p = get_object_or_404(Person, userid = request.user.username)
	m = get_object_or_404(Member, person = p, offering=course)
	try:
		grouplist = Group.objects.filter(courseoffering = course)
	except:
		grouplist = None
	memberlist = GroupMember.objects.none()
	if m.role == 'STUD':
		gs = Group.objects.filter(courseoffering=course, groupmember__student=m)
		g = None
		if gs is not None:
			try:
				g = gs.get(confirmed=True)
			except:
				g = None
		if g is not None:
			memberlist = GroupMember.objects.filter(group = g)
		else:
			memberlist = None
		return render_to_response('groups/student.html', {'course_slug':course_slug, 'groups':gs, 'group':g,'memberlist':memberlist,'grouplist':grouplist}, context_instance = RequestContext(request))
	elif m.role == 'INST':
		return render_to_response('groups/instructor.html', {'course_slug':course_slug, 'grouplist':grouplist}, context_instance = RequestContext(request))

@login_required
def create(request,course_slug):
	p = get_object_or_404(Person,userid=request.user.username)
	c = get_object_or_404(CourseOffering, slug = course_slug)
	group_manager=Member.objects.get(person = p, offering = c)
	return render_to_response('groups/create.html', {'manager':group_manager, 'course':c},context_instance = RequestContext(request)) 

@login_required
def submit(request,course_slug):
	p = get_object_or_404(Person,userid=request.user.username)
	c = get_object_or_404(CourseOffering, slug = course_slug)
	gm=Member.objects.get(person = p, offering = c)
	con = request.POST['GroupName']
	g = Group(name = con, manager = gm, courseoffering=c)
	g.save(); 
	
        return render_to_response('groups/succeed.html',context_instance=RequestContext(request))

@login_required
def join(request, course_slug, groupname):
	c = get_object_or_404(CourseOffering, slug=course_slug)
	g = get_object_or_404(Group, courseoffering = c, name = groupname)
	p = get_object_or_404(Person, userid = request.user.username)
	m = get_object_or_404(Member, person = p, offering=course)
	gm = GroupMember(group = g, student = m, confirmed = True)
	gm.save();
	return redirect(g, context_instance = RequestContext(request))
	
def joinconfirm(request):
	return render_to_response('groups/create.html', context_instance = RequestContext(request)) 
