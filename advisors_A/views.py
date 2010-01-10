from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from coredata.models import OtherUser, Person
from django.db.models import Q
from django.http import HttpResponse

@login_required
def index(request):
    userid = request.user.username
    memberships = OtherUser.objects.filter(person__userid=userid).filter(role='ADVS')
    return render_to_response("advisors_A/index.html", {'memberships': memberships}, context_instance=RequestContext(request))

@login_required
def search(request):
    if request.is_ajax():
	q = request.GET.get('q')
	results = None
	if q is not None:
	    results = Person.objects.filter(
		Q(emplid__contains = q) |
		Q(userid__contains = q) |
		Q(first_name__contains = q) |
		Q(last_name__contains = q) |
		Q(middle_name__contains = q) |
		Q(pref_first_name__contains = q)).order_by('last_name')
	print results
	return render_to_response("advisors_A/results.html", {'results':results}, context_instance=RequestContext(request))
    else:
	return HttpResponse('<h1>Page not found</h1>')
