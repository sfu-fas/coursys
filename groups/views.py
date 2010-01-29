# Create your views here.
from django.contrib.auth.decorators import login_required
from coredata.models import Member, Person
from group.models import *
from django.shortcuts import render_to_response, get_object_or_404

@login_required
def groupmanage(request):
	p = get_object_or_404(Person, userid = request.user.username)
	m = get_object_or_404(Member, person = p)
	grouplist = get_object_or_404(Group, courseoffering = request.courseoffering) #????
	if m.role == 'STUD':
		if g is None:
			c = False
		else:
			c = True
			memberlist = GroupMember.objects.get(group = g)
		render_to_response('group/student.html', {'group':g,'confirmed':c,'memberlist':memberlist,'grouplist':grouplist}, context_instance = RequestContext(request))
	else if m.role == 'INST':
		render_to_response('group/instructor.html', context_instance = RequestContext(request))