# Create your views here.
from django.contrib.auth.decorators import login_required
from coredata.models import Member, Person, CourseOffering
from groups.models import *
from django.shortcuts import render_to_response, get_object_or_404

@login_required
def groupmanage(request, course_slug):
	course = CourseOffering.objects.get(slug=course_slug)
	p = get_object_or_404(Person, userid = request.user.username)
	m = get_object_or_404(Member, person = p)
	grouplist = get_object_or_404(Group, courseoffering = course)
	if m.role == 'STUD':
		if g is None:
			c = False
		else:
			c = True
			memberlist = GroupMember.objects.get(group = g)
		render_to_response('groups/student.html', {'group':g,'confirmed':c,'memberlist':memberlist,'grouplist':grouplist}, context_instance = RequestContext(request))
	elif m.role == 'INST':
		render_to_response('groups/instructor.html', context_instance = RequestContext(request))