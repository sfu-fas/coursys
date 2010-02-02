# Create your views here.
from django.contrib.auth.decorators import login_required
from coredata.models import Member, Person, CourseOffering
from groups.models import *
from django.contrib.auth.decorators import login_required
from groups.models import *
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect

@login_required
def index(request):
	p = get_object_or_404(Person, userid = request.user.username)
	courselist = Member.objects.filter(person = p)
	return render_to_response('groups/index.html', {'courselist':courselist}, context_instance = RequestContext(request))

@login_required
def groupmanage(request, course_slug):
	course = CourseOffering.objects.get(slug=course_slug)
	p = get_object_or_404(Person, userid = request.user.username)
	m = get_object_or_404(Member, person = p, offering=course)
	try:
		grouplist = Group.objects.get(courseoffering = course)
	except:
		grouplist = None
	memberlist = GroupMember.objects.none()
	if m.role == 'STUD':
		#gm = GroupMember.objects.get(student = m).field()
		try:
			g = Group.objects.get(courseoffering=course, groupmember__student=m)
		except:
			g = None
		#g = gm.get(courseoffering=course)
		#return HttpResponse(str(g))
		if g is None:
			c = False
		else:
			c = True
			memberlist = GroupMember.objects.filter(group = g)
		return render_to_response('groups/student.html', {'group':g,'confirmed':c,'memberlist':memberlist,'grouplist':grouplist}, context_instance = RequestContext(request))
	elif m.role == 'INST':
		return render_to_response('groups/instructor.html', context_instance = RequestContext(request))
	else:
		return render_to_response('groups/instructor.html', context_instance = RequestContext(request))