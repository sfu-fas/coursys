from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from marking.models import *
from coredata.models import *

@login_required
def index(request):
    target_userid = request.user.username
    print target_userid
    person = Person.objects.get(userid = target_userid)
    print person
    courses = Member.objects.exclude(role="DROP").filter(offering__graded=True).filter(person__userid=target_userid) \
            .select_related('offering','offering__semester')
    print courses
    return render_to_response("marking/index.html", {'person':person, 'course_memberships':courses}, context_instance=RequestContext(request))
