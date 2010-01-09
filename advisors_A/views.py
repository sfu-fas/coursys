from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from coredata.models import OtherUser

@login_required
def index(request):
    userid = request.user.username
    memberships = OtherUser.objects.filter(person__userid=userid).filter(role='ADVS')
    return render_to_response("advisors_A/index.html", {'memberships': memberships}, context_instance=RequestContext(request))
